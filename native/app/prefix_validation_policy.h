// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <cstdint>
#include <initializer_list>
#include <utility>
#include <stdexcept>
namespace qwen_app {
inline void require_prefix_validation_policy(const nlohmann::json &policy) {
    const auto &p=policy.at("native_prefix_validation");
    if(!p.is_object()||p.size()!=16||p.at("schema")!="ps5-qwen-exact-prefix-validation-v1"||p.at("enabled")!=true||
       !p.at("prefix_reuse_enabled").is_boolean()||p.at("full_F32_logit_fingerprints")!=true||
       p.at("checkpoint_qualification_SELF_SHA256")!="b10752c83004a13f4941f5503b1557e5fe72c841057f29ec7553937918ebd1f0"||
       p.at("checkpoint_qualification_result_SHA256")!="e9d0db6bfb5b2d090e021c972cf14728f3a7d96b956c03b08946a60d6fdb50d7"||
       policy.contains("native_model_checkpoint_validation"))
        throw std::runtime_error("Exact independently qualified prefix validation policy required");
    for(const auto &item:std::initializer_list<std::pair<const char *,std::uint64_t>>{
        {"context_tokens",256},{"prefill_tokens",4},{"prompt_tokens",30},{"maximum_output_tokens",32},{"maximum_requests",2},
        {"maximum_state_bytes",142606336},{"maximum_metadata_bytes",1048576},{"maximum_additional_CPU_bytes",8388608},
        {"maximum_logit_records_per_request",33},{"additional_GPU_downloads",0}})
        if(!p.at(item.first).is_number_unsigned()||p.at(item.first)!=item.second)
            throw std::runtime_error("Prefix validation bounds differ");
    const auto &prefill=policy.at("native_prefill");const auto &routes=policy.at("native_expert_routes");
    if(prefill.at("schema")!="ps5-qwen-bounded-prefill-v1"||prefill.at("tokens")!=4u||
       prefill.at("all_prompt_outputs_requested")!=true||prefill.at("generated_token_batch_tokens")!=1u||
       routes.at("schema")!="ps5-qwen-completed-expert-routes-policy-v1"||routes.at("enabled")!=true||
       routes.at("maximum_records")!=4608u||routes.at("require_complete_48_layer_processes")!=true||routes.at("additional_GPU_downloads")!=0u)
        throw std::runtime_error("Prefix validation requires original prefill and completed route capture");
}
}
