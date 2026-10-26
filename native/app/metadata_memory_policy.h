// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline void require_metadata_memory_policy(const nlohmann::json &policy) {
    const nlohmann::json expected={{"schema","ps5-qwen-metadata-memory-policy-v1"},
        {"enabled",true},{"CPU_only",true},{"maximum_files",76u},{"phases_per_file",5u},
        {"maximum_records",380u},{"GPU_calls",0u},{"virtual_source_calls",0u},
        {"ordinary_OS_close_required",true}};
    const auto &p=policy.at("native_metadata_memory_diagnostic");
    if(p!=expected||!p.is_object()||p.size()!=expected.size()||
       !p.at("maximum_files").is_number_unsigned()||!p.at("phases_per_file").is_number_unsigned()||
       !p.at("maximum_records").is_number_unsigned()||!p.at("GPU_calls").is_number_unsigned()||
       !p.at("virtual_source_calls").is_number_unsigned()||
       policy.contains("native_prefix_validation")||policy.contains("native_model_checkpoint_validation")||
       policy.contains("native_source_stage_memory_diagnostic")||!policy.contains("native_direct_metadata")||
       !policy.contains("native_source_schedule"))
        throw std::runtime_error("Exact independent CPU-only metadata memory policy required");
}
}
