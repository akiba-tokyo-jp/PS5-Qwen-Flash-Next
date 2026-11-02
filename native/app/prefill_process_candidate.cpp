// SPDX-License-Identifier: MIT
// Pair this opt-in provider with the post-trunk Qwen model graph. It uses the
// exact pinned batch ABI and never changes decode/speculative output selection.
#include "llama.h"
#include "llama-batch.h"
#include <stdexcept>

#ifndef QWEN_PERF_PREFILL_POST_TRUNK
#define QWEN_PERF_PREFILL_POST_TRUNK 0
#endif
extern "C" bool qwen_app_route_is_decode();
extern "C" void qwen_native_stage(const char*);
extern "C" int32_t __real_llama_process(llama_context*,llama_process_type,llama_batch_ext*);

extern "C" int32_t __wrap_llama_process(llama_context*ctx,llama_process_type type,llama_batch_ext*batch){
    if(type!=LLAMA_PROCESS_TYPE_DECODE||qwen_app_route_is_decode())return __real_llama_process(ctx,type,batch);
    if(!batch||batch->tokens.empty()||batch->tokens.size()>32)
        throw std::runtime_error("Prefill candidate requires the current bounded nonempty batch");
    for(const auto&token:batch->tokens)if(!token.output)
        throw std::runtime_error("Prefill comparison requires the unchanged all-output control batch");
    const auto count=batch->tokens.size();
    if(QWEN_PERF_PREFILL_POST_TRUNK){
        for(std::size_t i=0;i<count;++i)
            if(!llama_batch_ext_set_output_logits(batch,int32_t(i),i+1==count))
                throw std::runtime_error("Prefill output selection failed before model processing");
    }
    qwen_native_stage(QWEN_PERF_PREFILL_POST_TRUNK?"P1_prefill_outputs_last":"P1_prefill_outputs_all");
    // The synchronous API captures the input batch before returning. Restore
    // caller-owned output flags on both return and exception paths.
    const auto restore=[&]{
        for(std::size_t i=0;i<count;++i)
            if(!llama_batch_ext_set_output_logits(batch,int32_t(i),true))
                throw std::runtime_error("Prefill output metadata restoration failed");
    };
    int32_t result;
    try{result=__real_llama_process(ctx,type,batch);}catch(...){restore();throw;}
    restore();return result;
}
