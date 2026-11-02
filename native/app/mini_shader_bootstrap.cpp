// SPDX-License-Identifier: MIT
// Reuse the exact CPU helpers and decoder; no driver or inference engine links.
#define main unused_mini_shader_memory_main
#include "mini_shader_memory.cpp"
#undef main
#include "mini_shader_bootstrap_policy.h"
int main(int argc,char **argv) {
    qwen_native_stage("mini_shader_bootstrap_CPU_main_entered_GPU_not_started");
    try {
        const auto startup=qwen_app::read_startup(argc,argv);
        std::ifstream input(startup.development_policy);const auto policy=Json::parse(input);
        const auto run=qwen_app::require_mini_shader_bootstrap_policy(policy,startup.first_generation_validation,
            startup.native_display,startup.admission_report);
        const auto &gate=policy.at("native_first_generation_validation");
        qwen_app::enable_native_memory_backpressure();require_model_CPU_budget();
        write_fresh_report(startup.admission_report+".first.start",{{"schema","ps5-qwen-first-generation-start-v1"},
            {"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",gate.at("candidate_SELF_sha256")},
            {"model_receipt_sha256",gate.at("model_receipt_sha256")},{"model_loaded",false},{"Vulkan_initialized",false}});
        qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",gate.at("candidate_SELF_bytes").get<std::uint64_t>(),
            gate.at("candidate_SELF_sha256").get<std::string>(),30);
        qwen_app::verify_native_startup_file_direct(startup.model_receipt,gate.at("model_receipt_bytes").get<std::uint64_t>(),
            gate.at("model_receipt_sha256").get<std::string>(),30);
        qwen_native_stage("complete_SELF_and_receipt_direct_SHA256_passed GPU_not_started=1");
        const auto before=diagnostic_VM_population();
        // The original memory-timing probe is deliberately not active: complete
        // asset verification has more read boundaries than its finite old scope.
        // Every original durable read marker and input/per-use SHA remains.
        admit_shader_storage_CPU(policy,startup.admission_report,true,run);
        require_model_CPU_budget();const auto assets=qwen_app::native_shader_asset_stats();
        if(assets.assets!=1527||assets.CPU_verified_assets!=1527||assets.lookup_entries!=382||
           assets.CPU_verified_lookups!=382||assets.active_lease||assets.failed||
           !assets.external_file.verified||assets.external_file.failed||assets.external_file.read_pending||
           assets.external_file.frame_requests!=1527)
            throw std::runtime_error("Complete current-run original shader verification did not finish");
        const auto after=diagnostic_VM_population();
        write_fresh_report(startup.admission_report+".CPU-bootstrap",{
            {"schema","ps5-qwen-mini-shader-bootstrap-result-v1"},{"pid",getpid()},{"run_id",run},
            {"VM_before",before},{"VM_after",after},{"CPU_verified_assets",assets.CPU_verified_assets},
            {"CPU_verified_lookups",assets.CPU_verified_lookups},{"registry_sha256",assets.registry_sha256},
            {"external_read_calls",assets.external_file.read_calls},{"external_returned_bytes",assets.external_file.returned_bytes},
            {"all_original_SPIRV_bytes_preserved",true},{"all_started_input_calls_returned",true},
            {"CPU_heap_cap_bytes",16u<<20},{"GPU_calls",0},{"model_loaded",false},
            {"source_workers",0},{"automatic_retries",0},{"ordinary_OS_close_required",true}});
        qwen_native_stage("mini_shader_bootstrap_CPU_completed_GPU_not_started_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
    }catch(const std::exception&e){
        char message[768];std::snprintf(message,sizeof(message),"mini_shader_bootstrap_CPU_returned_exception reason=%.680s",e.what());
        qwen_native_stage(message);
        qwen_native_stage("mini_shader_bootstrap_CPU_known_returned_refusal_GPU_not_started");qwen_native_halt("mini_shader_bootstrap_CPU_admission_refused");
    }catch(...){qwen_native_stage("mini_shader_bootstrap_CPU_known_returned_refusal_GPU_not_started");qwen_native_halt("mini_shader_bootstrap_CPU_admission_refused");}
}
