// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline std::string require_mini_shader_bootstrap_policy(const nlohmann::json &policy,
        bool first,bool display,const std::string &report) {
    using J=nlohmann::json;
    const J expected{{"schema","ps5-qwen-mini-shader-bootstrap-v1"},{"CPU_only",true},
        {"maximum_SELF_bytes",4u<<20},{"maximum_CPU_heap_bytes",16u<<20},
        {"complete_original_assets",1527},{"complete_original_lookups",382},
        {"GPU_calls",0},{"model_loads",0},{"source_workers",0},{"automatic_retries",0}};
    if(!first||display||policy.at("console_operations_enabled")!=true||
       policy.at("native_mini_shader_bootstrap")!=expected||
       policy.at("allowed_modes")!=J::array({"first-generation-validation"})||
       policy.contains("native_mini_shader_title")||policy.contains("native_shader_startup_memory_diagnostic"))
        throw std::runtime_error("Exact isolated current-run CPU bootstrap scope required");
    const auto &storage=policy.at("native_shader_storage");
    if(storage.at("verify_all_original_assets_before_Vulkan")!=true||storage.contains("prior_native_CPU"))
        throw std::runtime_error("CPU bootstrap must verify all original assets in this run");
    const auto &gate=policy.at("native_first_generation_validation");const auto run=gate.at("run_id").get<std::string>();
    const auto hex=[](const std::string &s,std::size_t n){return s.size()==n&&s.find_first_not_of("0123456789abcdef")==std::string::npos;};
    if(gate.size()!=5||!hex(run,32)||report!="/app0/qwen-runtime/plan-"+run+".json"||
       !gate.at("candidate_SELF_bytes").is_number_unsigned()||gate.at("candidate_SELF_bytes")==0||gate.at("candidate_SELF_bytes")>(4u<<20)||
       !gate.at("model_receipt_bytes").is_number_unsigned()||gate.at("model_receipt_bytes")==0||gate.at("model_receipt_bytes")>(1u<<20)||
       !hex(gate.at("candidate_SELF_sha256").get<std::string>(),64)||!hex(gate.at("model_receipt_sha256").get<std::string>(),64))
        throw std::runtime_error("CPU bootstrap requires exact bounded SELF/receipt/owner bindings");
    return run;
}
}
