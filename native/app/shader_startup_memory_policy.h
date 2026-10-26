// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline void require_shader_startup_memory_policy(const nlohmann::json &policy) {
    const nlohmann::json expected={{"schema","ps5-qwen-shader-startup-memory-v1"},{"enabled",true},
        {"CPU_only",true},{"maximum_stage_records",2048u},{"matched_idle_ns",2000000u},
        {"split_write_and_sync",true},{"stop_before_model_metadata",true},
        {"GPU_calls",0u},{"source_workers",0u},{"automatic_retries",0u}};
    const auto &p=policy.at("native_shader_startup_memory_diagnostic");
    if(!p.is_object()||p.size()!=expected.size()||p!=expected)
        throw std::runtime_error("Exact CPU-only shader startup attribution policy required");
    for(const auto *key:{"maximum_stage_records","matched_idle_ns","GPU_calls","source_workers","automatic_retries"})
        if(!p.at(key).is_number_unsigned())throw std::runtime_error("Shader startup attribution integer type differs");
    for(const auto *key:{"native_prefix_validation","native_model_checkpoint_validation","native_metadata_memory_diagnostic",
            "native_source_stage_memory_diagnostic","native_SELF_read_control","native_report_CPU_diagnostic","native_frame_CPU_diagnostic"})
        if(policy.contains(key))throw std::runtime_error("Shader startup attribution must be an independent finite CPU case");
    if(!policy.contains("native_first_generation_validation")||!policy.contains("native_boundary_memory_diagnostic")||
       !policy.contains("native_source_schedule")||policy.at("native_source_schedule").at("startup_integrity_direct")!=true||
       policy.at("native_shader_storage").at("verify_all_original_assets_before_Vulkan")!=false||
       !policy.at("native_shader_storage").contains("prior_native_CPU"))
        throw std::runtime_error("Shader startup attribution requires original Direct integrity, bounded observations and qualified prior shader evidence");
}
}
