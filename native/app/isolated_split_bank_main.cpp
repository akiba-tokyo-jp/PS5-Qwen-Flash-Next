// SPDX-License-Identifier: MIT
// The generated prefix preserves the current isolated title's shared admission
// helpers verbatim. No model, chat, whole-model metadata or source mapping loop.
#include "isolated_split_startup.inc"
#include "split_bank_admission.h"
int main(int argc,char **argv) {
    bool resources=false;std::string report;Json snapshots=Json::array();
    const auto observe=[&](const char *phase){
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);const auto memory=qwen_app::observe_native_system_memory();
        snapshots.push_back({{"phase",phase},{"VM",diagnostic_VM_population()},{"CPU_heap_mapped_bytes",heap.mapped_bytes},
            {"CPU_heap_peak_bytes",heap.peak_bytes},{"CPU_heap_libc_fallbacks",heap.libc_fallbacks},
            {"Flexible_available_bytes",memory.flexible_available},{"kernel_free_pages",memory.kernel_free},{"kernel_startup_target_pages",memory.kernel_target}});
    };
    try {
        qwen_native_stage("isolated_split_bank_main_entered_GPU_not_started");observe("main_entered");
        const auto startup=qwen_app::read_startup(argc,argv);report=startup.admission_report;qwen_native_set_fault_report((report+".fatal").c_str());
        std::ifstream file(startup.development_policy);const auto policy=Json::parse(file);
        qwen_app::require_split_bank_policy(policy,startup.first_generation_validation,startup.native_display,bool(startup.clock_calibration));
        const auto &binding=policy.at("native_isolated_split_bank_title");const auto run=binding.at("run_id").get<std::string>();
        if(report!="/app0/qwen-runtime/plan-"+run+".json")throw std::runtime_error("Split backing requires the exact fresh report binding");
        llama_log_set(native_log,nullptr);ggml_log_set(native_log,nullptr);qwen_app::enable_native_memory_backpressure();require_model_CPU_budget();
        qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",binding.at("candidate_SELF_bytes").get<std::uint64_t>(),binding.at("candidate_SELF_sha256").get<std::string>(),30);
        observe("SELF_integrity_completed");qwen_app::admit_cpu_runtime(qwen_native_stage);qwen_app::inspect_vulkan_globals();
        admit_shader_storage_CPU(policy,report,true,Json(run));observe("CPU_shader_completed");
        (void)qwen_app::admit_native_startup_memory();
        std::int64_t physical=0;std::size_t available=0,flexible=0;const auto pool=sceKernelGetDirectMemorySize();
        if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&available)<0||sceKernelAvailableFlexibleMemorySize(&flexible)<0||
           available<(1ull<<30)||flexible<(64u<<20))throw std::runtime_error("Split backing requires the unchanged Direct/Flexible setup headroom");
        observe("before_source_and_GPU_scope");auto result=qwen_app::admit_split_bank_backing(policy,report+".driver.log",resources);qwen_native_driver_complete();
        const auto shaders=qwen_app::native_shader_asset_stats();
        if(!shaders.initialized||shaders.failed||shaders.active_lease||shaders.external_file.read_pending||!shaders.external_file.verified||
           shaders.CPU_verified_assets||shaders.decoded_calls+shaders.raw_calls==0||shaders.external_file.frame_requests!=shaders.decoded_calls+shaders.raw_calls)
            throw std::runtime_error("Split backing shader input leases did not retire");
        observe("GPU_scope_completed");result.update({{"pid",getpid()},{"run_id",run},{"candidate_SELF_sha256",binding.at("candidate_SELF_sha256")},
            {"positive_device_idle_and_epoch_retirement",true},{"current_complete_shader_file_SHA256_checked",true},
            {"all_used_shader_inputs_SHA256_checked",true},{"all_shader_input_leases_returned",true},
            {"shader_module_inputs",shaders.decoded_calls+shaders.raw_calls},{"memory_observations",snapshots},
            {"Direct_available_before_GPU",available},{"Flexible_available_before_GPU",flexible},{"automatic_retries",0}});
        write_fresh_report(report,result);qwen_native_stage("split_bank_validation_completed_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
    }catch(const std::exception &error) {
        if(resources)qwen_native_driver_retain();qwen_native_stage("isolated_split_bank_exception_after_work_stopped");
        if(!report.empty())try{write_fresh_report(report+".failure",{{"message",error.what()},{"native_GPU_scope_started",resources},{"observations",snapshots},{"model_loaded",false}});}catch(...){}
        for(;;)(void)usleep(1000000);
    }
}
