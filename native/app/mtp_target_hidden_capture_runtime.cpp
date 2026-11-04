// SPDX-License-Identifier: MIT
#include "mtp_target_hidden_capture_runtime.h"
#include "llama-ext.h"
#include <ps5platform/heap.h>
#include <stdexcept>
extern "C" {
llama_batch_ext*__real_llama_batch_ext_init(llama_context*);
void __real_llama_batch_ext_free(llama_batch_ext*);
void __real_llama_batch_ext_clear(llama_batch_ext*);
int32_t __real_llama_batch_ext_add_token(llama_batch_ext*,llama_seq_id,llama_token);
int32_t __real_llama_process(llama_context*,llama_process_type,llama_batch_ext*);
void __real_llama_synchronize(llama_context*);
}
namespace {
using Capture=qwen_app::MtpTargetHiddenCapture<>;
struct RegisteredBatch {llama_batch_ext*batch;llama_context*context;};
// Only bounded pointer bookkeeping exists before admission. Hidden arrays live
// on the tracked heap after an actual target context is supplied.
RegisteredBatch registry[16]{};
Capture*capture=nullptr;
bool registry_overflow=false;
float*get(void*context,int index){return llama_get_embeddings_nextn_ith(static_cast<llama_context*>(context),index);}
void synchronize(void*context){__real_llama_synchronize(static_cast<llama_context*>(context));}
}
extern "C" llama_batch_ext*__wrap_llama_batch_ext_init(llama_context*context){
    auto*batch=__real_llama_batch_ext_init(context);
    if(batch){
        bool stored=false;
        for(auto&row:registry)if(!row.batch||row.batch==batch){row={batch,context};stored=true;break;}
        if(!stored)registry_overflow=true;
        if(capture)capture->batch_created(batch,context);
    }
    return batch;
}
extern "C" void __wrap_llama_batch_ext_free(llama_batch_ext*batch){
    __real_llama_batch_ext_free(batch);
    for(auto&row:registry)if(row.batch==batch)row={};
    if(capture)capture->batch_freed(batch);
}
extern "C" void __wrap_llama_batch_ext_clear(llama_batch_ext*batch){
    __real_llama_batch_ext_clear(batch);if(capture)capture->batch_cleared(batch);
}
extern "C" int32_t __wrap_llama_batch_ext_add_token(llama_batch_ext*batch,llama_seq_id sequence,llama_token token){
    const auto index=__real_llama_batch_ext_add_token(batch,sequence,token);
    if(capture)capture->token_added(batch,index);return index;
}
extern "C" int32_t __wrap_llama_process(llama_context*context,llama_process_type type,llama_batch_ext*batch){
    const auto result=__real_llama_process(context,type,batch);
    if(capture)capture->original_process_returned(context,batch,result);return result;
}
extern "C" void __wrap_llama_synchronize(llama_context*context){
    __real_llama_synchronize(context);if(capture)capture->original_synchronize_returned(context);
}
namespace qwen_app {
void bind_mtp_target_hidden_capture(llama_context*context){
    if(!context||registry_overflow)throw std::runtime_error("Exact bounded target batch registry required before hidden capture");
    if(!capture){
        capture=new Capture({get,synchronize});
        if(!ps5_heap_owns(capture))throw std::runtime_error("Target hidden capture requires the tracked CPU heap");
        for(const auto&row:registry)if(row.batch)capture->batch_created(row.batch,row.context);
    }
    capture->bind_target(context);llama_set_embeddings_nextn(context,true,true);
    if(capture->failed())throw std::runtime_error("Target hidden capture metadata admission failed");
}
const MtpTargetHiddenCapture<>*mtp_target_hidden_capture()noexcept{return capture;}
void retire_mtp_target_hidden_capture_after_all_owners(){delete capture;capture=nullptr;}
}
