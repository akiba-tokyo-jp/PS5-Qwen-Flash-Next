// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline nlohmann::json model_relative_prefetch_scope(bool enabled){
    return {{"schema","ps5-qwen-relative-model-prefetch-v1"},{"kind","I1-relative-model-prefetch"},
        {"requests",3},{"model_loads",1},{"HTTP_requests",0},{"VideoOut_starts",0},
        {"prefetch_enabled",enabled},{"original_cold_retained_exact_prefix_sequence",true},
        {"scratch_bytes",2u<<20},{"maximum_extra_workers",1},{"maximum_pending_spans",1},
        {"maximum_total_parallel_reads",4},{"maximum_predictions_per_original_producer",6},
        {"maximum_original_producers",8},{"additional_source_FDs",0},{"descriptor_identity_fields",12},
        {"original_close_waits_for_same_pending_read",true},{"unknown_completion_retains_actual_backing",true},
        {"model_math_and_GPU_unchanged",true},{"persistent_caches",false},{"GPU_calls_added",0}};
}
inline bool require_model_relative_prefetch_scope(const nlohmann::json&actual){
    if(!actual.is_object()||!actual.contains("prefetch_enabled")||!actual.at("prefetch_enabled").is_boolean())
        throw std::runtime_error("One exact boolean relative-prefetch arm is required");
    const bool enabled=actual.at("prefetch_enabled").get<bool>();const auto expected=model_relative_prefetch_scope(enabled);
    if(actual.size()!=expected.size())throw std::runtime_error("Exact bounded relative-prefetch fields are required");
    for(auto item=expected.begin();item!=expected.end();++item){
        const auto&value=actual.at(item.key());
        if((item.value().is_number_integer()?!value.is_number_integer():value.type()!=item.value().type())||value!=item.value())
            throw std::runtime_error("An original relative-prefetch bound or owner contract differs");
    }
    return enabled;
}
}
