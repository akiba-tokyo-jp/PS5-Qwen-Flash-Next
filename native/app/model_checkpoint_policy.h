// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline void require_model_checkpoint_policy(const nlohmann::json &policy) {
    const auto &p=policy.at("native_model_checkpoint_validation");
    if(!p.is_object()||p.size()!=14||p.at("schema")!="ps5-qwen-model-checkpoint-validation-v1"||p.at("enabled")!=true||
       !p.at("request_ordinal").is_number_unsigned()||p.at("request_ordinal")!=2u||
       !p.at("context_tokens").is_number_unsigned()||p.at("context_tokens")!=256u||
       !p.at("prefill_tokens").is_number_unsigned()||p.at("prefill_tokens")!=4u||
       !p.at("maximum_output_tokens").is_number_unsigned()||p.at("maximum_output_tokens")!=32u||
       p.at("prefill_positions")!=nlohmann::json::array({4,28})||
       !p.at("maximum_captures").is_number_unsigned()||p.at("maximum_captures")!=34u||
       !p.at("maximum_state_bytes").is_number_unsigned()||p.at("maximum_state_bytes")!=142606336u||
       !p.at("maximum_metadata_bytes").is_number_unsigned()||p.at("maximum_metadata_bytes")!=1048576u||
       !p.at("maximum_additional_CPU_bytes").is_number_unsigned()||p.at("maximum_additional_CPU_bytes")!=8388608u||
       !p.at("absolute_logit_tolerance").is_number_float()||p.at("absolute_logit_tolerance")!=1e-5||
       !p.at("relative_logit_tolerance").is_number_float()||p.at("relative_logit_tolerance")!=1e-5||
       p.at("performance_adoption_enabled")!=false)
        throw std::runtime_error("Exact bounded complete-model checkpoint validation policy required");
    for(const auto &position:p.at("prefill_positions"))if(!position.is_number_unsigned())
        throw std::runtime_error("Checkpoint prefill positions must retain the original batch geometry");
    const auto &prefill=policy.at("native_prefill");const auto &routes=policy.at("native_expert_routes");
    if(prefill.at("schema")!="ps5-qwen-bounded-prefill-v1"||prefill.at("tokens")!=4u||
       prefill.at("all_prompt_outputs_requested")!=true||prefill.at("generated_token_batch_tokens")!=1u||
       routes.at("schema")!="ps5-qwen-completed-expert-routes-policy-v1"||routes.at("enabled")!=true||
       routes.at("maximum_records")!=4608u||routes.at("require_complete_48_layer_processes")!=true||routes.at("additional_GPU_downloads")!=0u)
        throw std::runtime_error("Checkpoint validation requires unchanged bounded prefill and completed route capture");
}
}
