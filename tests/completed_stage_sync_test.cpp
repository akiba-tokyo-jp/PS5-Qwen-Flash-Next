// SPDX-License-Identifier: MIT
#include <initializer_list>
#include <string>
#include "completed_stage_sync.h"
int main(){
    for(const char *phase:{"inference_tokenization_completed","inference_decode_synchronization_completed",
            "inference_prefill_completed","inference_token_ready","inference_end_of_generation_observed",
            "inference_request_reset_completed","inference_exact_prefix_prefill_restored_completed"}){
        if(!qwen_app::completed_inference_stage(phase))return 1;
        for(const auto &changed:{std::string(phase)+"_before",std::string("before_")+phase})
            if(qwen_app::completed_inference_stage(changed.c_str()))return 2;
    }
    for(const char *phase:{"inference_before_tokenization","inference_before_prefill","inference_before_decode_call",
            "inference_decode_call_returned_before_synchronize","inference_before_sampling",
            "inference_before_successful_request_reset","native_driver_before_positive_device_idle",
            "native_driver_device_idle_completed","unknown_completed","",static_cast<const char*>(nullptr)})
        if(qwen_app::completed_inference_stage(phase))return 3;
    return 0;
}
