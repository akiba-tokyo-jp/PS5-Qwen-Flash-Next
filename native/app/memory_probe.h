// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>

namespace qwen_app {
inline std::string require_memory_probe_policy(const nlohmann::json & policy, bool display) {
    const auto & p=policy.at("native_memory_validation");
    const auto phase=p.at("phase").get<std::string>();
    if(display || p.at("schema")!="ps5-qwen-native-memory-validation-v1" ||
       (phase!="telemetry" && phase!="virtual-16KiB" && phase!="direct-io") ||
       p.at("fresh_idle_session_bound_by_launcher")!=true ||
       p.at("original_numerical_readmission_passed_this_boot")!=true ||
       p.at("model_loading_enabled")!=false || p.at("Vulkan_initialization_enabled")!=false ||
       !p.at("maximum_virtual_probe_bytes").is_number_unsigned() || p.at("maximum_virtual_probe_bytes")!=16384u ||
       !p.at("maximum_io_window_bytes").is_number_unsigned() || p.at("maximum_io_window_bytes")!=(8u<<20))
        throw std::runtime_error("A bounded, model-independent native memory policy is required");
    if(phase!="telemetry" && p.at("preceding_telemetry_and_normal_close_passed_this_boot")!=true)
        throw std::runtime_error("Native telemetry and normal close must pass before the virtual probe");
    if(phase=="direct-io" && p.at("preceding_virtual_probe_and_normal_close_passed_this_boot")!=true)
        throw std::runtime_error("The tiny virtual probe and normal close must pass before direct I/O");
    return phase;
}
nlohmann::json observe_native_memory();
nlohmann::json run_native_memory_probe(const nlohmann::json & policy);
}
