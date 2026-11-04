// SPDX-License-Identifier: MIT
#pragma once
#include <cstring>
#include <initializer_list>

namespace qwen_app {
// A returned decode call is deliberately excluded: synchronization is still
// pending. Unknown phases and every before-operation phase remain durable.
inline bool completed_inference_stage(const char *phase) {
    if(!phase)return false;
    for(const char *known:{"inference_tokenization_completed",
            "inference_decode_synchronization_completed","inference_prefill_completed",
            "inference_token_ready","inference_end_of_generation_observed",
            "inference_request_reset_completed","inference_exact_prefix_prefill_restored_completed"})
        if(std::strcmp(phase,known)==0)return true;
    return false;
}
}
