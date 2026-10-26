// SPDX-License-Identifier: MIT
#include "model_checkpoint.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <string>
namespace qwen_app {
struct ModelCheckpoint::Payload {
    CheckpointApplicationState application;
    std::vector<std::uint8_t> metadata;
    std::vector<float> logits;
    llama_pos minimum=-1,maximum=-1;
    std::uint64_t bytes=0;
};
namespace {void check(bool value,const char *message){if(!value)throw std::runtime_error(message);}}
ModelCheckpoint::ModelCheckpoint(llama_model *model,llama_context *context)
    :model_(model),context_(context),owner_(std::this_thread::get_id()),data_(new Payload){}
ModelCheckpoint::~ModelCheckpoint() {
    // Quarantine retains metadata together with the external context/GPU owner.
    if(status_!=Status::capturing&&status_!=Status::restoring&&status_!=Status::quarantined)delete data_;
}
void ModelCheckpoint::owner()const {
    check(owner_==std::this_thread::get_id(),"Checkpoint requires its original producer");
    check(model_&&context_&&status_!=Status::quarantined&&status_!=Status::capturing&&status_!=Status::restoring,
        "Checkpoint owner is pending or quarantined");
    check(llama_get_model(context_)==model_,"Checkpoint context belongs to another model");
}
void ModelCheckpoint::capture(const CheckpointApplicationState &state,const float *values,std::size_t count,
    const Admit &admit,const Stage &stage,const Complete &complete) {
    owner();check(admit&&stage&&complete,"Checkpoint requires admission, durable stages and positive completion");
    const auto *vocab=llama_model_get_vocab(model_);const auto memory=llama_get_memory(context_);
    check(vocab&&memory&&values&&count>0&&count<=262144&&count==std::size_t(llama_vocab_n_tokens(vocab)),"Checkpoint vocabulary/logit owner differs");
    check(state.request_epoch&&state.position>0&&std::uint32_t(state.position)<=llama_n_ctx(context_)&&
        !state.prompt.empty()&&state.prompt.size()<=64&&(state.pending==LLAMA_TOKEN_NULL||(state.pending>=0&&std::size_t(state.pending)<count)),
        "Checkpoint application state exceeds the admitted sequence");
    for(const auto value:state.prompt)check(value>=0&&std::size_t(value)<count,"Checkpoint prompt IDs exceed the original vocabulary");
    for(std::size_t i=0;i<count;++i)check(std::isfinite(values[i]),"Checkpoint logits are nonfinite");
    const auto flags=LLAMA_STATE_SEQ_FLAGS_ON_DEVICE;
    const auto metadata=llama_state_seq_get_size_ext(context_,0,flags);
    const auto full=llama_state_seq_get_size_ext(context_,0,LLAMA_STATE_SEQ_FLAGS_NONE);
    check(metadata&&metadata<=(1u<<20)&&full>metadata&&full-metadata<=(136u<<20),"Complete state does not fit the bounded device/CPU checkpoint scope");
    admit(full-metadata);
    data_->application=state;data_->metadata.resize(metadata);data_->logits.assign(values,values+count);
    check(data_->metadata.capacity()<=(1u<<20)&&data_->logits.capacity()<=262144,"Checkpoint CPU metadata capacity exceeds its bound");
    data_->minimum=llama_memory_seq_pos_min(memory,0);data_->maximum=llama_memory_seq_pos_max(memory,0);
    const auto binding="model_checkpoint_memory_binding minimum="+std::to_string(data_->minimum)+" maximum="+std::to_string(data_->maximum)+" application_position="+std::to_string(state.position);
    stage(binding.c_str());
    check(data_->minimum>=0&&data_->maximum>=data_->minimum&&data_->maximum<state.position,"Checkpoint memory positions disagree with application state");
    data_->bytes=full-metadata;
    status_=Status::capturing;
    try {
        stage("model_checkpoint_capture_before_GPU owners_pinned=1");
        const auto got=llama_state_seq_get_data_ext(context_,data_->metadata.data(),data_->metadata.size(),0,flags);
        stage("model_checkpoint_capture_API_returned owners_pinned=1");
        check(got==data_->metadata.size(),"Device checkpoint API did not return its complete metadata");
        complete();stage("model_checkpoint_capture_GPU_completed owners_pinned=1");status_=Status::saved;
    }catch(...){status_=Status::quarantined;throw;}
}
const CheckpointApplicationState &ModelCheckpoint::restore(std::uint64_t epoch,const Stage &stage,const Complete &complete) {
    owner();check(status_==Status::saved&&epoch&&epoch==data_->application.request_epoch&&stage&&complete,
        "Checkpoint restore requires the saved request/model/context binding");
    status_=Status::restoring;
    try {
        stage("model_checkpoint_restore_before_GPU owners_pinned=1");
        const auto got=llama_state_seq_set_data_ext(context_,data_->metadata.data(),data_->metadata.size(),0,LLAMA_STATE_SEQ_FLAGS_ON_DEVICE);
        stage("model_checkpoint_restore_API_returned owners_pinned=1");
        check(got==data_->metadata.size(),"Device checkpoint restore did not consume every metadata byte");
        complete();stage("model_checkpoint_restore_GPU_completed owners_pinned=1");
        const auto memory=llama_get_memory(context_);
        check(memory&&llama_memory_seq_pos_min(memory,0)==data_->minimum&&llama_memory_seq_pos_max(memory,0)==data_->maximum,
            "Restored sequence positions differ");
        stage("model_checkpoint_restore_positions_verified");status_=Status::saved;return data_->application;
    }catch(...){status_=Status::quarantined;throw;}
}
const std::vector<float> &ModelCheckpoint::logits()const {owner();check(status_==Status::saved,"No saved checkpoint logits exist");return data_->logits;}
void ModelCheckpoint::discard(){owner();status_=Status::empty;data_->application={};data_->metadata.clear();data_->logits.clear();data_->bytes=0;}
bool ModelCheckpoint::saved()const{return status_==Status::saved;}
bool ModelCheckpoint::quarantined()const{return status_==Status::quarantined;}
std::uint64_t ModelCheckpoint::payload_bytes()const{owner();return data_->bytes;}
std::size_t ModelCheckpoint::metadata_bytes()const{owner();return data_->metadata.size();}
}
