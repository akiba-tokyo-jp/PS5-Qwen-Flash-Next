// SPDX-License-Identifier: MIT
#include "speculative_batch_probe.h"
#include "llama-memory.h"
#include "llama-io.h"
#include "ggml-backend.h"
#include <cstring>
#include <stdexcept>
extern "C" {
#include "hash/sha256/sha256.h"
}

namespace qwen_app {
namespace {
SpeculativeBatchProbe *active=nullptr;
std::string hex(const std::array<unsigned char,32>&value){
    const char *digits="0123456789abcdef";std::string out;out.reserve(64);
    for(auto byte:value){out+=digits[byte>>4];out+=digits[byte&15];}return out;
}
class StateWriter final:public llama_io_write_i {
    sha256_t metadata_,tensors_,geometry_;
    std::array<unsigned char,65536> window_{};
public:
    ProbeStateDigest result;
    StateWriter(){sha256_init(&metadata_);sha256_init(&tensors_);sha256_init(&geometry_);}
    void write(const void *data,std::size_t bytes)override{
        if(!data||bytes>(1u<<20)||result.metadata_bytes+bytes>(1u<<20))throw std::runtime_error("Probe state metadata exceeds its bound");
        sha256_update(&metadata_,static_cast<const unsigned char*>(data),bytes);result.metadata_bytes+=bytes;
    }
    void write_tensor(ggml_tensor *tensor,std::size_t offset,std::size_t bytes)override{
        if(!tensor||tensor->type!=GGML_TYPE_F32||!bytes||bytes%4||offset>ggml_nbytes(tensor)||bytes>ggml_nbytes(tensor)-offset||
           result.tensor_bytes+bytes>(136u<<20)||++result.tensor_sections>512)
            throw std::runtime_error("Probe requires the original bounded active F32 state");
        const std::uint64_t geometry[]={std::uint64_t(tensor->type),std::uint64_t(bytes)};
        sha256_update(&geometry_,reinterpret_cast<const unsigned char*>(geometry),sizeof(geometry));
        for(std::size_t done=0;done<bytes;){
            const auto part=std::min(window_.size(),bytes-done);
            ggml_backend_tensor_get(tensor,window_.data(),offset+done,part);
            sha256_update(&tensors_,window_.data(),part);done+=part;++result.readback_calls;
        }
        result.tensor_bytes+=bytes;
    }
    std::size_t n_bytes()override{return result.metadata_bytes+result.tensor_bytes;}
    ProbeStateDigest finish(llama_memory_t memory){
        sha256_final(&metadata_,result.metadata.data());sha256_final(&tensors_,result.tensors.data());sha256_final(&geometry_,result.geometry.data());
        result.minimum=llama_memory_seq_pos_min(memory,0);result.maximum=llama_memory_seq_pos_max(memory,0);
        if(!result.tensor_bytes||!result.tensor_sections||result.minimum<0||result.maximum<result.minimum)
            throw std::runtime_error("Probe active original state is incomplete");
        return result;
    }
};
bool same(const ProbeStateDigest&a,const ProbeStateDigest&b){
    return a.metadata==b.metadata&&a.tensors==b.tensors&&a.geometry==b.geometry&&a.metadata_bytes==b.metadata_bytes&&
        a.tensor_bytes==b.tensor_bytes&&a.tensor_sections==b.tensor_sections&&a.minimum==b.minimum&&a.maximum==b.maximum;
}
nlohmann::json state_report(const ProbeStateDigest&s){return {{"metadata_SHA256",hex(s.metadata)},{"active_tensor_SHA256",hex(s.tensors)},
    {"tensor_geometry_SHA256",hex(s.geometry)},{"metadata_bytes",s.metadata_bytes},{"active_tensor_bytes",s.tensor_bytes},
    {"tensor_sections",s.tensor_sections},{"bounded_readback_calls",s.readback_calls},{"minimum_position",s.minimum},{"maximum_position",s.maximum}};}
}
nlohmann::json logit_difference_report(const LogitDifference&s){return {{"columns",s.columns},{"all_finite",s.finite},
    {"outside_original_tolerance",s.outside_tolerance},{"maximum_absolute_error",s.maximum},{"RMS_error",s.rms},
    {"p50_absolute_error",s.p50},{"p95_absolute_error",s.p95},{"p99_absolute_error",s.p99},{"mean_shift",s.mean_shift},
    {"mean_centered_RMS_error",s.centered_rms},{"KL_reference_to_candidate",s.KL_reference_to_candidate},
    {"reference_top5",s.reference_top},{"candidate_top5",s.candidate_top},
    {"reference_top1_margin",s.reference_margin},{"candidate_top1_margin",s.candidate_margin}};}
SpeculativeBatchProbe::SpeculativeBatchProbe(std::size_t columns):columns_(columns),reference_(2*columns),scratch_(columns){
    if(active||columns<5||columns>262144)throw std::runtime_error("One bounded original producer probe required");active=this;
}
SpeculativeBatchProbe::~SpeculativeBatchProbe(){if(active==this)active=nullptr;}
void SpeculativeBatchProbe::arm(bool enabled){
    if(owner_!=std::this_thread::get_id())throw std::runtime_error("Probe requires its original producer");
    enabled_=enabled;observations_=0;accepted_=bonus_=false;committed_position_=-1;states_={};comparisons_={};
}
bool SpeculativeBatchProbe::requested()const{return enabled_&&observations_==0;}
void SpeculativeBatchProbe::observe(unsigned kind,llama_context *context,const float *first,const float *second){
    if(!enabled_||owner_!=std::this_thread::get_id()||kind!=observations_||kind>2||!context||!first||!second)
        throw std::runtime_error("Probe two-row/state observation is out of order");
    if(kind==0){std::copy(first,first+columns_,reference_.data());std::copy(second,second+columns_,reference_.data()+columns_);}
    else{
        comparisons_[2*(kind-1)]=compare_logits(first,reference_.data(),columns_,scratch_.data());
        comparisons_[2*(kind-1)+1]=compare_logits(second,reference_.data()+columns_,columns_,scratch_.data());
    }
    llama_synchronize(context);auto memory=llama_get_memory(context);
    if(!memory)throw std::runtime_error("Probe original memory owner missing");
    StateWriter writer;memory->state_write(writer,0,LLAMA_STATE_SEQ_FLAGS_NONE);states_[kind]=writer.finish(memory);++observations_;
}
void SpeculativeBatchProbe::decision(bool accepted,std::int32_t position,bool bonus){
    if(observations_!=3||owner_!=std::this_thread::get_id())throw std::runtime_error("Probe decision precedes complete state observation");
    accepted_=accepted;bonus_=bonus;committed_position_=position;
}
nlohmann::json SpeculativeBatchProbe::report()const{
    nlohmann::json rows=nlohmann::json::array(),states=nlohmann::json::array();bool logits=true;
    for(const auto&s:comparisons_){rows.push_back(logit_difference_report(s));logits=logits&&s.finite&&s.columns==columns_&&!s.outside_tolerance;}
    for(const auto&s:states_)states.push_back(state_report(s));
    return {{"schema","ps5-qwen-same-batch-probe-v1"},{"enabled",enabled_},{"observations",observations_},
        {"ordinary_repeat_and_candidate_rows",rows},{"ordinary_reference_repeat_candidate_states",states},
        {"same_width_logits_within_original_tolerance",logits&&observations_==3},
        {"ordinary_repeat_active_state_bit_exact",observations_==3&&same(states_[0],states_[1])},
        {"candidate_active_state_bit_exact",observations_==3&&same(states_[0],states_[2])},
        {"draft_actually_accepted",accepted_},{"bonus_logits_pinned",bonus_},{"committed_position",committed_position_},
        {"readback_window_bytes",65536},{"class_layout_changed",false},{"speed_measurement",false}};
}
bool speculative_batch_probe_requested(){return active&&active->requested();}
void speculative_batch_probe_observe(unsigned kind,llama_context*c,const float*a,const float*b){if(!active)throw std::runtime_error("Probe owner missing");active->observe(kind,c,a,b);}
void speculative_batch_probe_decision(bool accepted,std::int32_t position,bool bonus){if(!active)throw std::runtime_error("Probe owner missing");active->decision(accepted,position,bonus);}
}
