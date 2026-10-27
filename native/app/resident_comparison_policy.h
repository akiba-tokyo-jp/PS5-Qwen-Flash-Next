// SPDX-License-Identifier: MIT
#pragma once
#include "first_generation_policy.h"
#include <nlohmann/json.hpp>
namespace qwen_app {
inline nlohmann::json resident_comparison_scope(bool CPU_calibration=false) {
    return {{"schema","ps5-qwen-resident-comparison-v1"},{"enabled",true},
        {"CPU_startup_calibration",CPU_calibration},{"CPU_preparation_uses_operational_floor",true},
        {"maximum_requests",CPU_calibration?0:10},{"warmup_requests",CPU_calibration?0:1},{"matched_arms_per_candidate",CPU_calibration?0:4},
        {"forced_rejection_requests",CPU_calibration?0:1},{"context_tokens",256},{"prefill_tokens",4},
        {"active_cache_slots",53},{"maximum_output_tokens",32},{"model_loads",CPU_calibration?0:1},
        {"GPU_start_reference_pages",3563},
        {"HTTP_requests",0},{"VideoOut_starts",0},{"legacy_transport_scope_overridden",true},
        {"all_original_precision_preserved",true},{"automatic_retries",0},
        {"performance_adoption_enabled",false}};
}
inline void require_resident_comparison_policy(const nlohmann::json &p) {
    // The legacy gate still validates immutable model/provenance bindings. The
    // explicit resident scope alone defines this test's request count/transport.
    require_first_generation_policy(p,false);
    const auto &scope=p.at("native_resident_comparison");
    if(!scope.at("CPU_startup_calibration").is_boolean())throw std::runtime_error("Typed CPU calibration selector required");
    const bool calibration=scope.at("CPU_startup_calibration").get<bool>();
    const auto expected=resident_comparison_scope(calibration);
    if(!scope.is_object()||scope.size()!=expected.size())
        throw std::runtime_error("Complete exact resident scope required");
    for(auto i=expected.begin();i!=expected.end();++i){
        const auto &v=scope.at(i.key());
        if((i.value().is_number_integer()?!v.is_number_integer():v.type()!=i.value().type())||v!=i.value())
            throw std::runtime_error("Resident scope value or type differs");
    }
    if(p.at("native_resident_comparison")!=resident_comparison_scope(calibration)||
       p.at("console_operations_enabled")!=true||p.at("console_validation_enabled")!=true||p.at("deployment_enabled")!=false||
       p.at("allowed_modes")!=nlohmann::json::array({"first-generation-validation"})||
       p.at("native_prefill").at("tokens")!=4||p.at("native_padded_expert_cache").at("active_slots")!=53||
       p.at("native_padded_expert_cache").at("cache_cap_bytes")!=536870912||
       !p.contains("native_source_schedule")||!p.contains("native_expert_routes"))
        throw std::runtime_error("Exact independent resident comparison scope required");
    for(const auto *key:{"native_CPU_phase_control","native_SELF_read_control",
        "native_cache_layout_phase_memory","native_frame_CPU_diagnostic","native_large_cache_scope",
        "native_mapped_streaming_copy","native_metadata_memory_diagnostic","native_model_free_speculation",
        "native_owned_mapped_probe","native_padded_bank_layout_probe","native_predictive_cache",
        "native_report_CPU_diagnostic","native_shader_startup_memory_diagnostic",
        "native_source_contention_probe","native_source_stage_memory_diagnostic","native_direct_frame_evidence"})
        if(p.contains(key))throw std::runtime_error("Unrelated experiment in resident comparison");
}
}
