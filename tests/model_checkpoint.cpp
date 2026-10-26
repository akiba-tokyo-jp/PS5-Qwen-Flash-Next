// SPDX-License-Identifier: MIT
// Transaction and owner stubs only. No learned model or GPU is executed here.
#include "model_checkpoint.h"
#include <array>
#include <atomic>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>
struct llama_vocab {};
struct llama_model {llama_vocab vocab;};
struct llama_memory_i {llama_pos minimum=0,maximum=7;std::array<std::uint8_t,96> state{},saved{};};
struct llama_context {llama_model *model;llama_memory_i memory;};
namespace {
unsigned captures=0,restores=0,completions=0,refused=0;bool short_capture=false,short_restore=false,wrong_position=false;
std::size_t metadata_size=16,payload_size=96;std::vector<std::string> stages;
void check(bool v){if(!v)throw std::runtime_error("Model checkpoint transaction invariant failed");}
template<class F>void reject(F f){bool caught=false;try{f();}catch(...){caught=true;}check(caught);++refused;}
}
extern "C" {
const llama_model *llama_get_model(const llama_context *ctx){return ctx->model;}
const llama_vocab *llama_model_get_vocab(const llama_model *model){return &model->vocab;}
int32_t llama_vocab_n_tokens(const llama_vocab *){return 32;}
uint32_t llama_n_ctx(const llama_context *){return 256;}
llama_memory_t llama_get_memory(const llama_context *ctx){return const_cast<llama_memory_i *>(&ctx->memory);}
llama_pos llama_memory_seq_pos_min(llama_memory_t memory,llama_seq_id seq){check(seq==0);return memory->minimum;}
llama_pos llama_memory_seq_pos_max(llama_memory_t memory,llama_seq_id seq){check(seq==0);return memory->maximum;}
size_t llama_state_seq_get_size_ext(llama_context *,llama_seq_id seq,llama_state_seq_flags flags){check(seq==0);return metadata_size+(flags==LLAMA_STATE_SEQ_FLAGS_ON_DEVICE?0:payload_size);}
size_t llama_state_seq_get_data_ext(llama_context *ctx,uint8_t *dst,size_t size,llama_seq_id seq,llama_state_seq_flags flags){
    check(seq==0&&flags==LLAMA_STATE_SEQ_FLAGS_ON_DEVICE&&size==16);++captures;ctx->memory.saved=ctx->memory.state;
    const std::int32_t header[4]={0xaf143cd,seq,ctx->memory.minimum,ctx->memory.maximum};std::memcpy(dst,header,16);return short_capture?size-1:size;
}
size_t llama_state_seq_set_data_ext(llama_context *ctx,const uint8_t *src,size_t size,llama_seq_id seq,llama_state_seq_flags flags){
    check(seq==0&&flags==LLAMA_STATE_SEQ_FLAGS_ON_DEVICE&&size==16);++restores;std::int32_t header[4];std::memcpy(header,src,16);
    ctx->memory.minimum=header[2];ctx->memory.maximum=header[3]+(wrong_position?1:0);ctx->memory.state=ctx->memory.saved;return short_restore?size-1:size;
}
}
int main() {
    llama_model model,other;llama_context context{&model,{}};std::vector<float> logits(32);
    for(unsigned i=0;i<32;++i)logits[i]=float(i)/17;
    for(unsigned i=0;i<96;++i)context.memory.state[i]=std::uint8_t(i*37+17);
    const auto original=context.memory.state;
    qwen_app::CheckpointApplicationState app{1,8,5,true,{1,2,3}};
    auto admit=[](std::uint64_t bytes){check(bytes==96);};auto stage=[](const char *s){stages.emplace_back(s);};auto complete=[]{++completions;};
    qwen_app::ModelCheckpoint saved(&model,&context);
    reject([&]{saved.restore(1,stage,complete);});
    saved.capture(app,logits.data(),logits.size(),admit,stage,complete);check(saved.saved()&&saved.payload_bytes()==96&&saved.metadata_bytes()==16);
    context.memory.state.fill(91);context.memory.maximum=15;
    const auto restored=saved.restore(1,stage,complete);check(restored.position==8&&restored.pending==5&&restored.ready&&restored.prompt==app.prompt);
    check(saved.logits()==logits&&context.memory.state==original&&context.memory.maximum==7);
    const auto before=restores;reject([&]{saved.restore(2,stage,complete);});check(restores==before);
    std::atomic<bool> foreign{false};std::thread child([&]{try{saved.logits();}catch(...){foreign=true;}});child.join();check(foreign);
    context.model=&other;reject([&]{saved.restore(1,stage,complete);});context.model=&model;
    saved.discard();reject([&]{saved.restore(1,stage,complete);});
    for(unsigned variant=0;variant<6;++variant) {
        auto bad=app;auto bad_logits=logits;const auto old=captures;
        if(variant==0)bad.request_epoch=0;if(variant==1)bad.position=0;if(variant==2)bad.prompt.clear();
        if(variant==3)bad_logits[0]=std::numeric_limits<float>::quiet_NaN();if(variant==4)metadata_size=1u<<21;if(variant==5)payload_size=137u<<20;
        reject([&]{saved.capture(bad,bad_logits.data(),bad_logits.size(),admit,stage,complete);});check(captures==old);metadata_size=16;payload_size=96;
    }
    app.request_epoch=2;app.pending=LLAMA_TOKEN_NULL;app.ready=false;
    saved.capture(app,logits.data(),logits.size(),admit,stage,complete);
    const auto partial=saved.restore(2,stage,complete);check(!partial.ready&&partial.pending==LLAMA_TOKEN_NULL&&partial.request_epoch==2);
    for(unsigned variant=0;variant<4;++variant) {
        qwen_app::ModelCheckpoint failed(&model,&context);
        if(variant==0)short_capture=true;
        if(variant==0)reject([&]{failed.capture(app,logits.data(),logits.size(),admit,stage,complete);});
        else {
            failed.capture(app,logits.data(),logits.size(),admit,stage,complete);
            if(variant==1)short_restore=true;if(variant==2)wrong_position=true;
            reject([&]{failed.restore(2,stage,variant==3?qwen_app::ModelCheckpoint::Complete([]{throw std::runtime_error("Uncertain completion");}):complete);});
        }
        check(failed.quarantined());reject([&]{failed.discard();});
        short_capture=false;short_restore=false;wrong_position=false;context.memory.maximum=7;
    }
    check(captures==6&&restores==5&&completions==8);
    std::cout<<"{\"full_stub_state_and_application_roundtrip\":true,\"partial_prefill_state\":true,\"wrong_epoch_model_and_thread_refused\":true,\"bounded_failure_controls\":"<<refused
        <<",\"uncertain_cases_retained\":4,\"CPU_whole_state_payload\":false,\"PS5_operations\":0,\"model_arithmetic\":false}"<<std::endl;
}
