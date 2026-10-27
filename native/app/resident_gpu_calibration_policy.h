// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline nlohmann::json resident_gpu_calibration_scope() {
    return {{"schema","ps5-qwen-resident-GPU-initialization-calibration-v3"},{"enabled",true},
        {"CPU_preflight_required",false},{"static_GPU_resources_preflight_required",true},
        {"whole_model_metadata_files",0},{"source_workers",0},{"total_above_kernel_minimum_pages",512},
        {"original_operational_floor_unchanged",true},{"prior_positive_VM_population_growth_pages",226},
        {"sampled_Direct_metadata_pages",17},{"sampled_idle_pages",2},
        {"prior_full_GPU_fixture_case",2840},{"prior_full_GPU_fixture_global_decline_pages",103},
        {"prior_full_GPU_fixture_result_sha256","d596ba7c1c149b9b8819f095826063bf972f6ef2f612cad2a019641b05861411"},
        {"maximum_backend_instances",1},{"model_loads",0},{"graph_computes",0},
        {"tensor_payload_allocations",0},{"model_requests",0},
        {"ordinary_OS_close_required",true},{"original_completion_guards_required",true},
        {"automatic_retries",0}};
}
inline std::uint64_t resident_gpu_phase_component(const nlohmann::json &report) {
    const auto &before=report.at("VM_before_GPU");const auto &after=report.at("VM_after_GPU_and_retirement");
    std::uint64_t positive=0;
    for(const auto *field:{"wired","active"}) {
        const auto a=before.at(field).get<std::uint64_t>(),b=after.at(field).get<std::uint64_t>();
        if(b>a)positive+=b-a;
    }
    if(positive!=226)throw std::runtime_error("Exact earlier full-fixture VM observations required");
    // This is a sampled population-movement proxy, not exclusive ownership
    // or a proven instantaneous peak. The larger fixture includes this init.
    return positive+17+2;
}
inline void require_resident_gpu_calibration_policy(const nlohmann::json &p) {
    const auto &scope=p.at("native_resident_GPU_initialization_calibration");
    const auto expected=resident_gpu_calibration_scope();
    if(!scope.is_object()||scope.size()!=expected.size()||
       !p.at("native_resident_comparison").at("CPU_startup_calibration").get<bool>())
        throw std::runtime_error("Exact model-free GPU initializer calibration required");
    for(auto i=expected.begin();i!=expected.end();++i) {
        const auto &value=scope.at(i.key());
        if((i.value().is_number_integer()?!value.is_number_integer():value.type()!=i.value().type())||value!=i.value())
            throw std::runtime_error("GPU initializer calibration scope value or type differs");
    }
}
}
