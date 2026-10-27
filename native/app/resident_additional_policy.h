// SPDX-License-Identifier: MIT
#pragma once
#include "first_generation_policy.h"
#include <nlohmann/json.hpp>
namespace qwen_app {
inline nlohmann::json resident_additional_scope(const std::string &kind,unsigned slots) {
    if((kind!="cache"&&kind!="prefix")||(slots!=53&&slots!=128)||(kind=="prefix"&&slots!=53))
        throw std::runtime_error("Unsupported isolated resident comparison");
    const bool prefix=kind=="prefix";
    return {{"schema","ps5-qwen-resident-additional-comparison-v1"},{"kind",kind},{"enabled",true},
        {"CPU_startup_calibration",false},{"CPU_preparation_uses_operational_floor",true},
        {"maximum_requests",prefix?9:3},{"warmup_requests",1},{"matched_groups",prefix?4:1},
        {"requests_per_group",2},{"forced_rejection_requests",0},{"context_tokens",256},
        {"prefill_tokens",4},{"active_cache_slots",slots},{"maximum_output_tokens",32},{"model_loads",1},
        {"HTTP_requests",0},{"VideoOut_starts",0},{"legacy_transport_scope_overridden",true},
        {"all_original_precision_preserved",true},{"automatic_retries",0},{"performance_adoption_enabled",false}};
}
inline void require_resident_additional_policy(const nlohmann::json &policy,const std::string &kind) {
    require_first_generation_policy(policy,false);
    const auto &scope=policy.at("native_resident_comparison");
    const auto &cache=policy.at("native_padded_expert_cache");
    const unsigned slots=cache.at("active_slots").get<unsigned>();
    const auto expected=resident_additional_scope(kind,slots);
    if(!scope.is_object()||scope.size()!=expected.size())throw std::runtime_error("Exact additional scope required");
    for(auto i=expected.begin();i!=expected.end();++i) {
        const auto &v=scope.at(i.key());
        if((i.value().is_number_integer()?!v.is_number_integer():v.type()!=i.value().type())||v!=i.value())
            throw std::runtime_error("Additional scope value or type differs");
    }
    if(policy.at("console_operations_enabled")!=true||policy.at("console_validation_enabled")!=true||
       policy.at("deployment_enabled")!=false||
       policy.at("allowed_modes")!=nlohmann::json::array({"first-generation-validation"})||
       policy.at("native_prefill").at("tokens")!=4||
       cache.at("cache_cap_bytes")!=(slots==53?536870912ull:1274462208ull)||
       policy.contains("native_large_cache_scope")!=(slots==128)||
       !policy.contains("native_source_schedule")||!policy.contains("native_expert_routes"))
        throw std::runtime_error("Isolated geometry and original route/source accounting required");
    for(const auto *key:{"native_CPU_phase_control","native_SELF_read_control","native_cache_layout_phase_memory",
        "native_frame_CPU_diagnostic","native_mapped_streaming_copy","native_metadata_memory_diagnostic",
        "native_model_free_speculation","native_owned_mapped_probe","native_padded_bank_layout_probe",
        "native_predictive_cache","native_report_CPU_diagnostic","native_shader_startup_memory_diagnostic",
        "native_source_contention_probe","native_source_stage_memory_diagnostic","native_direct_frame_evidence",
        "native_model_checkpoint_validation","native_prefix_validation","native_resident_GPU_initialization_calibration",
        "native_resident_GPU_buffer_capacity","native_resident_GPU_capacity_only"})
        if(policy.contains(key))throw std::runtime_error("Unrelated experiment in additional resident comparison");
}
}
