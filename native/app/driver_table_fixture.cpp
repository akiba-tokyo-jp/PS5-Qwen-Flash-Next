// SPDX-License-Identifier: MIT
// Minimal changed-driver qualification. No model loading, HTTP server or display.
#include "driver_tables.h"
#include "shader_assets.h"
#include "model_cpu_budget.h"
#include "system_memory.h"
#include "profile_clock.h"
#include "direct_integrity.h"
#include "model_integrity.h"
#include "startup.h"
#include "stage_memory_probe.h"
#include "boundary_memory_trace.h"
#include "runtime_admission.h"
#include "vulkan_admission.h"
#include "gpu_admission.h"
#include "native_gpu.h"
#include <ps5platform/heap.h>
#include <ps5platform/kernel.h>
#include <nlohmann/json.hpp>
#include <array>
#include <chrono>
#include <fstream>
#include <string>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <fcntl.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
void qwen_native_stage(const char *);
[[noreturn]] void qwen_native_halt(const char *);
}
using Json=nlohmann::json;
using ModelFileIdentity=std::array<std::uint64_t,10>;
#include "mini_shader_boundaries.inc"
static void write_fresh_report(const std::string &path,const Json &report){
    const auto data=report.dump(2)+"\n";
    if(data.size()>(1u<<20))throw std::runtime_error("Driver-table fixture report exceeds its bound");
    int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    if(fd<0)throw std::runtime_error("Fresh fixture report could not be opened");
    bool ok=!fchmod(fd,0644);std::size_t at=0;
    while(ok&&at<data.size()){const auto got=write(fd,data.data()+at,data.size()-at);if(got<=0)ok=false;else at+=got;}
    if(ok)ok=!fsync(fd);const bool closed=!close(fd);
    if(!ok||!closed)throw std::runtime_error("Driver-table fixture report did not positively persist");
}
static void require_model_CPU_budget(){struct ps5_heap_stats h{};ps5_heap_stats(&h);
    if(h.libc_fallbacks||h.mapped_bytes>qwen_app::maximum_model_CPU_heap_bytes||h.peak_bytes>qwen_app::maximum_model_CPU_heap_bytes)
        throw std::runtime_error("The unchanged tracked CPU heap cap is required");
    (void)qwen_app::admit_native_system_memory();}
#include "mini_shader_admission.inc"
int main(int argc,char **argv){bool GPU=false;std::string report_path;
    qwen_native_stage("driver_table_fixture_main_entered_GPU_not_started");
    try {
        const auto startup=qwen_app::read_startup(argc,argv);report_path=startup.admission_report;
        std::ifstream file(startup.development_policy);const auto policy=Json::parse(file);
        const Json scope{{"schema","ps5-qwen-driver-table-fixture-v1"},{"model_loads",0u},{"GPU_graphs",1u},
            {"matrix_columns",32u},{"matrix_rows",16u},{"weights","BF16"},{"accumulation","F32"},{"automatic_retries",0u}};
        if(!startup.first_generation_validation||startup.native_display||policy.at("console_operations_enabled")!=true||
           policy.at("native_driver_table_fixture")!=scope||policy.at("allowed_modes")!=Json::array({"first-generation-validation"})||
           !&qwen_driver_table_storage||qwen_driver_table_storage.count<640||qwen_driver_table_storage.count>1024)
            throw std::runtime_error("The isolated exact driver-table fixture scope is required");
        const auto &binding=policy.at("native_first_generation_validation");const auto run=binding.at("run_id").get<std::string>();
        if(run.size()!=32||run.find_first_not_of("0123456789abcdef")!=std::string::npos||
           startup.admission_report!="/app0/qwen-runtime/plan-"+run+".json")
            throw std::runtime_error("Exact current title binding and fresh report path required");
        qwen_app::enable_native_memory_backpressure();boundary_memory_enabled=true;
        const auto before=diagnostic_VM_population();
        qwen_app::restore_native_driver_tables();
        const auto restored=diagnostic_VM_population();
        qwen_native_stage("driver_table_fixture_all_constants_restored_readonly_GPU_not_started");
        qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",binding.at("candidate_SELF_bytes").get<std::uint64_t>(),
            binding.at("candidate_SELF_sha256").get<std::string>(),30);
        qwen_app::verify_native_startup_file_direct(startup.model_receipt,binding.at("model_receipt_bytes").get<std::uint64_t>(),
            binding.at("model_receipt_sha256").get<std::string>(),30);
        admit_shader_storage_CPU(policy,startup.admission_report,true,run);
        const auto after_integrity=diagnostic_VM_population();
        write_fresh_report(report_path+".first.start",{{"schema","ps5-qwen-first-generation-start-v1"},{"pid",getpid()},
            {"run_id",run},{"candidate_SELF_sha256",binding.at("candidate_SELF_sha256")},
            {"model_receipt_sha256",binding.at("model_receipt_sha256")},{"model_loaded",false},{"Vulkan_initialized",false}});
        write_fresh_report(report_path+".CPU",{{"schema","ps5-qwen-driver-table-startup-v1"},{"run_id",run},{"pid",getpid()},
            {"tables",qwen_driver_table_storage.count},{"all_original_constants_restored_readonly",true},{"VM_main_entry",before},
            {"VM_after_restoration",restored},{"VM_after_integrity",after_integrity},{"GPU_calls",0u},{"model_loaded",false}});
        (void)qwen_app::admit_native_startup_memory();
        std::int64_t physical=0;std::size_t available=0,flexible=0;const auto pool=sceKernelGetDirectMemorySize();
        if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&available)<0||
           sceKernelAvailableFlexibleMemorySize(&flexible)<0||available<(1ull<<30)||flexible<(64u<<20))
            throw std::runtime_error("Unchanged GPU memory-pool admission refused");
        const auto start=std::chrono::steady_clock::now();if(usleep(250000))throw std::runtime_error("Clock control refused");
        const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        if(ms<200||ms>2000)throw std::runtime_error("Clock scale control refused");
        if(setenv("MESA_SHADER_CACHE_DISABLE","true",1)||setenv("GGML_VK_DISABLE_ASYNC","1",1)||
           setenv("GGML_VK_SERIALIZE_SUBMISSIONS","1",1)||setenv("GGML_VK_MAX_NODES_PER_SUBMIT","1",1)||
           setenv("GGML_VK_BOUNDED_STAGING","1",1))throw std::runtime_error("Required serialized cache policy refused");
        qwen_app::admit_cpu_runtime(qwen_native_stage);qwen_app::inspect_vulkan_globals();
        if(!qwen_native_gpu_frontend_linked())throw std::runtime_error("Native frontend absent");
        GPU=true;qwen_native_gpu_initialize((report_path+".driver.log").c_str());qwen_native_driver_begin();
        const auto result=qwen_app::admit_bf16_gpu(qwen_native_stage);
        qwen_native_driver_complete();
        if(!result.passed)throw std::runtime_error("The original BF16 numerical fixture failed");
        write_fresh_report(report_path,{{"schema","ps5-qwen-driver-table-GPU-result-v1"},{"run_id",run},{"pid",getpid()},
            {"candidate_SELF_sha256",binding.at("candidate_SELF_sha256")},{"complete",true},{"all_original_constants_restored_readonly",true},
            {"passed",result.passed},{"expected",result.expected},{"actual",result.actual},{"max_absolute_error",result.max_absolute_error},
            {"positive_device_idle_and_epoch_retirement",true},{"model_loaded",false},{"GPU_graphs",1u},{"full_model_speed_qualified",false}});
        qwen_native_stage("driver_table_fixture_GPU_completed_waiting_for_ordinary_close");
    }catch(const std::exception &e){
        if(GPU){qwen_native_driver_retain();qwen_native_halt("driver_table_fixture_retained_GPU_failure");}
        if(!report_path.empty())try{write_fresh_report(report_path+".failure",{{"schema","ps5-qwen-driver-table-CPU-refusal-v1"},
            {"message",e.what()},{"pid",getpid()},{"GPU_calls",0u},{"model_loaded",false},{"unknown_completion",false}});}catch(...){qwen_native_halt("driver_table_fixture_CPU_report_failed");}
        qwen_native_stage("driver_table_fixture_known_returned_CPU_refusal_GPU_not_started");
    }
    for(;;)(void)usleep(1000000);
}
