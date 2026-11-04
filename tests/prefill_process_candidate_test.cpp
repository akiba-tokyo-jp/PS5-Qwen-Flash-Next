// SPDX-License-Identifier: MIT
// The harness supplies minimal batch types; actual ABI compilation is separate.
#include "prefill_process_candidate.cpp"
#include <algorithm>
#include <cassert>
#include <cstdio>

struct llama_context{};struct llama_sampler{};struct llama_token_data_array{};
static bool expect_prefill=false,throw_process=false;
static unsigned calls=0,stages=0;
extern "C" void qwen_native_stage(const char*){++stages;}
extern "C" int32_t __real_llama_process(llama_context*,llama_process_type,llama_batch_ext*batch){
    ++calls;unsigned outputs=0;for(const auto&t:batch->tokens)outputs+=t.output;
    assert(outputs==(expect_prefill&&QWEN_PERF_PREFILL_POST_TRUNK?1:batch->tokens.size()));
    if(throw_process)throw std::runtime_error("Injected synchronous processing failure");
    return 0;
}
extern "C" void __real_llama_sampler_apply(llama_sampler*,llama_token_data_array*){}
extern "C" llama_token __real_llama_sampler_sample(llama_sampler*,llama_context*,int32_t){return 7;}
static llama_batch_ext batch(unsigned count,int first){
    llama_batch_ext result;result.tokens.resize(count);
    for(unsigned i=0;i<count;++i){result.tokens[i].output=true;result.tokens[i].pos[0]=first+int(i);}
    return result;
}
static void process(llama_context*ctx,unsigned count,int first,bool prefill){
    auto value=batch(count,first);expect_prefill=prefill;
    assert(__wrap_llama_process(ctx,LLAMA_PROCESS_TYPE_DECODE,&value)==0);
    assert(std::all_of(value.tokens.begin(),value.tokens.end(),[](const auto&t){return t.output;}));
}
int main(){
    llama_context ctx;llama_sampler sampler;llama_token_data_array data;
    const unsigned lengths[]={1,2,31,32,33,63,64,65};
    for(unsigned repeat=0;repeat<2;++repeat)for(auto length:lengths){
        for(unsigned pos=0;pos<length;){const auto n=std::min(32u,length-pos);process(&ctx,n,int(pos),true);pos+=n;}
        if(repeat)__wrap_llama_sampler_apply(&sampler,&data);
        else assert(__wrap_llama_sampler_sample(&sampler,&ctx,-1)==7);
        process(&ctx,1,int(length),false);process(&ctx,2,int(length+1),false);
    }
    auto value=batch(2,0);expect_prefill=true;throw_process=true;
    bool caught=false;try{__wrap_llama_process(&ctx,LLAMA_PROCESS_TYPE_DECODE,&value);}catch(const std::runtime_error&){caught=true;}
    assert(caught&&value.tokens[0].output&&value.tokens[1].output);throw_process=false;
    __wrap_llama_sampler_apply(&sampler,&data);
    value=batch(2,0);value.tokens[0].output=false;caught=false;
    const auto before=calls;try{__wrap_llama_process(&ctx,LLAMA_PROCESS_TYPE_DECODE,&value);}catch(const std::runtime_error&){caught=true;}
    assert(caught&&calls==before&&!value.tokens[0].output&&value.tokens[1].output);
    std::printf("Prefill phase/flag controls passed: last_only=%u boundaries=8 repetitions=2 decode_widths=1,2 exception_restore=1\n",
                unsigned(QWEN_PERF_PREFILL_POST_TRUNK));assert(stages>0);
}
