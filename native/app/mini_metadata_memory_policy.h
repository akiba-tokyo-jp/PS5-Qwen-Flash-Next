// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline std::string require_mini_metadata_memory_policy(const nlohmann::json &policy,
        bool first,bool display,const std::string &report) {
    using J=nlohmann::json;
    const J expected={{"schema","ps5-qwen-mini-metadata-memory-v1"},{"CPU_only",true},
        {"maximum_SELF_bytes",4u<<20},{"maximum_CPU_heap_bytes",64u<<20},
        {"original_containers",76},{"ordered_records",380},{"GPU_calls",0},
        {"source_workers",0},{"virtual_source_calls",0},{"model_loads",0},{"automatic_retries",0}};
    if(!first||display||policy.at("console_operations_enabled")!=true||
       policy.at("allowed_modes")!=J::array({"first-generation-validation"})||
       policy.at("native_mini_metadata_memory")!=expected)
        throw std::runtime_error("Exact isolated CPU metadata attribution scope required");
    for(const auto key:{"native_large_cache_scope","native_cache_layout_phase_memory","native_shader_storage",
            "native_prefix_validation","native_model_checkpoint_validation","native_model_free_speculation"})
        if(policy.contains(key))throw std::runtime_error("CPU metadata cannot combine GPU, shader or model experiments");
    const auto &gate=policy.at("native_first_generation_validation");const auto run=gate.at("run_id").get<std::string>();
    const auto hex=[](const std::string &s,std::size_t n){return s.size()==n&&s.find_first_not_of("0123456789abcdef")==std::string::npos;};
    if(gate.size()!=5||!hex(run,32)||report!="/app0/qwen-runtime/plan-"+run+".json"||
       !gate.at("candidate_SELF_bytes").is_number_unsigned()||gate.at("candidate_SELF_bytes")==0||gate.at("candidate_SELF_bytes")>(4u<<20)||
       !gate.at("model_receipt_bytes").is_number_unsigned()||gate.at("model_receipt_bytes")==0||gate.at("model_receipt_bytes")>(1u<<20)||
       !hex(gate.at("candidate_SELF_sha256").get<std::string>(),64)||!hex(gate.at("model_receipt_sha256").get<std::string>(),64)||
       !policy.at("native_metadata_source_seal").is_object())
        throw std::runtime_error("CPU metadata requires bounded SELF/receipt/run and original source-seal bindings");
    return run;
}
}
