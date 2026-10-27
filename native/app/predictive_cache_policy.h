// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline void require_predictive_cache_policy(const nlohmann::json &policy) {
    const nlohmann::json expected={{"schema","ps5-qwen-predictive-cache-v1"},{"enabled",true},
        {"active_cache_slots",53},{"maximum_predicted_experts",1},{"maximum_source_reads",1},
        {"original_expert_roles",3},{"forecast_contexts",512},{"forecast_targets",16},
        {"minimum_prior_observations",2},{"minimum_frequency_numerator",3},
        {"minimum_frequency_denominator",4},{"protect_current_route",true},
        {"actual_backing_lease_required",true},{"join_before_source_or_slot_mutation",true},
        {"wait_ms",10000},{"automatic_retries",0},{"performance_adoption_enabled",false}};
    if(policy.at("native_predictive_cache")!=expected||!policy.contains("native_padded_expert_cache")||
       policy.at("native_prefill").at("tokens")!=4||policy.contains("native_large_cache_scope")||
       policy.contains("native_model_free_speculation")||policy.contains("native_model_checkpoint_validation")||
       policy.contains("native_prefix_validation"))
        throw std::runtime_error("The independent original-precision predictive-cache scope is required");
}
}
