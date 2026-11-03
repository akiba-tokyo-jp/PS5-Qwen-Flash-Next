// SPDX-License-Identifier: MIT
#include "prefill_cold_candidate.cpp"
#include <algorithm>
#include <cassert>
#include <cstdlib>
struct llama_context{};struct llama_sampler{};struct llama_token_data_array{};
static bool expect_narrow=false,inject_failure=false;
static unsigned calls;
extern "C" void qwen_native_stage(const char*){}
extern "C" int32_t __real_llama_process(llama_context*,llama_process_type,llama_batch_ext*b){
    ++calls;unsigned outputs=0;for(const auto&t:b->tokens)outputs+=t.output;
    assert(outputs==(expect_narrow?1:b->tokens.size()));
    if(inject_failure)throw std::runtime_error("Injected synchronous P1 failure");return 0;
}
extern "C" void __real_llama_sampler_apply(llama_sampler*,llama_token_data_array*){}
extern "C" llama_token __real_llama_sampler_sample(llama_sampler*,llama_context*,int32_t){return 7;}
static void select_failure(unsigned ordinal,bool enabled){bool caught=false;try{qwen_P1_select_request(ordinal,enabled);}catch(...){caught=true;}assert(caught);}
static void process(llama_context*ctx,unsigned count,int pos,bool narrow){
    llama_batch_ext b;b.tokens.resize(count);
    for(unsigned i=0;i<count;++i){b.tokens[i].output=true;b.tokens[i].pos[0]=pos+int(i);}
    expect_narrow=narrow;bool caught=false;
    try{__wrap_llama_process(ctx,LLAMA_PROCESS_TYPE_DECODE,&b);}catch(...){caught=true;}
    assert(caught==inject_failure&&std::all_of(b.tokens.begin(),b.tokens.end(),[](const auto&t){return t.output;}));
}
int main(int argc,char**argv){
    assert(argc==3);const unsigned length=unsigned(std::atoi(argv[1]));const bool enabled=std::atoi(argv[2])!=0;
    assert(length&&length<=65);llama_context ctx;llama_sampler sampler;llama_token_data_array data;
    select_failure(1,enabled);qwen_P1_select_request(0,enabled);
    for(unsigned pos=0;pos<length;){unsigned n=std::min(32u,length-pos);process(&ctx,n,int(pos),enabled);pos+=n;}
    select_failure(1,enabled);assert(__wrap_llama_sampler_sample(&sampler,&ctx,-1)==7);
    process(&ctx,1,int(length),false);process(&ctx,2,int(length+1),false);
    select_failure(1,!enabled);qwen_P1_select_request(1,enabled);
    for(unsigned pos=0;pos<length;){unsigned n=std::min(32u,length-pos);process(&ctx,n,int(pos),false);pos+=n;}
    __wrap_llama_sampler_apply(&sampler,&data);qwen_P1_select_request(2,enabled);
    // Exact-prefix restoration can reach decode without any prefill call.
    process(&ctx,1,int(length),false);process(&ctx,2,int(length+1),false);
    inject_failure=true;process(&ctx,2,0,false);inject_failure=false;
    __wrap_llama_sampler_apply(&sampler,&data);select_failure(3,enabled);assert(calls>0);
    return 0;
}
