// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline std::string require_mini_virtual_source_policy(const nlohmann::json &policy,bool first,bool display,const std::string &report) {
    using J=nlohmann::json;
    const J expected={{"schema","ps5-qwen-mini-virtual-source-v1"},{"CPU_only",true},
        {"maximum_SELF_bytes",4u<<20},{"maximum_CPU_heap_bytes",64u<<20},{"maximum_live_regions",8},
        {"maximum_virtual_bytes",32ull<<30},{"source_indices",J::array({7,8,9,10,11,12,13,14})},
        {"modes",J::array({"per_file","shared_arena","shared_arena","per_file"})},
        {"match_native_journal_marker_count",true},{"quiet_seconds_before_rounds",5},
        {"extra_kernel_pages_before_round",512},{"GPU_calls",0},{"model_loads",0},
        {"model_payload_reads",0},{"source_workers",0},{"automatic_retries",0}};
    if(!first||display||policy.at("console_operations_enabled")!=true||
       policy.at("allowed_modes")!=J::array({"first-generation-validation"})||
       policy.at("native_mini_virtual_source")!=expected)
        throw std::runtime_error("Exact bounded CPU virtual-source comparison required");
    for(const auto name:{"native_large_cache_scope","native_cache_layout_phase_memory","native_shader_storage",
            "native_prefix_validation","native_model_checkpoint_validation","native_model_free_speculation"})
        if(policy.contains(name))throw std::runtime_error("CPU virtual-source comparison cannot combine model or GPU experiments");
    const auto &gate=policy.at("native_first_generation_validation");const auto run=gate.at("run_id").get<std::string>();
    const auto hex=[](const std::string &s,std::size_t n){return s.size()==n&&s.find_first_not_of("0123456789abcdef")==std::string::npos;};
    if(gate.size()!=5||!hex(run,32)||report!="/app0/qwen-runtime/plan-"+run+".json"||
       !gate.at("candidate_SELF_bytes").is_number_unsigned()||gate.at("candidate_SELF_bytes")==0||gate.at("candidate_SELF_bytes")>(4u<<20)||
       !gate.at("model_receipt_bytes").is_number_unsigned()||gate.at("model_receipt_bytes")==0||gate.at("model_receipt_bytes")>(1u<<20)||
       !hex(gate.at("candidate_SELF_sha256").get<std::string>(),64)||!hex(gate.at("model_receipt_sha256").get<std::string>(),64))
        throw std::runtime_error("The CPU virtual-source SELF/receipt binding is invalid");
    const auto &proof=policy.at("native_completed_metadata");const auto source_run=proof.at("run_id").get<std::string>();
    if(proof.size()!=6||!hex(source_run,32)||proof.at("report_path")!="/app0/qwen-runtime/plan-"+source_run+".json.metadata-memory"||
       !proof.at("report_bytes").is_number_unsigned()||proof.at("report_bytes")==0||proof.at("report_bytes")>(1u<<20)||
       !proof.at("pid").is_number_integer()||proof.at("pid")<=0||!hex(proof.at("report_sha256").get<std::string>(),64)||
       proof.at("SELF_sha256")!="7757d6dd79bc406945ee8a9688f1ca4e9ead80adc7981f66f540f73dfde787f6")
        throw std::runtime_error("The complete qualified CPU metadata report is required");
    return run;
}
}
