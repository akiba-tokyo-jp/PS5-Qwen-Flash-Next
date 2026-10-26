// SPDX-License-Identifier: MIT
// Weightless PLE title: original shared CPU admission and Vulkan fixture only.
#include "shader_assets.h"
#include "boundary_memory_trace.h"
#include "model_cpu_budget.h"
#include "system_memory.h"
#include "direct_integrity.h"
#include "startup.h"
#include "runtime_admission.h"
#include "vulkan_admission.h"
#include "ple_slice_admission.h"
#include "native_gpu.h"
#include "mapped_source_bridge.h"
#include "ggml.h"
#include "llama.h"
#include <ps5platform/heap.h>
#include <ps5platform/kernel.h>
#include <nlohmann/json.hpp>
#include <array>
#include <algorithm>
#include <cstring>
#include <fstream>
#include <string>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <fcntl.h>
#include <unistd.h>
extern "C" {
#include "hash/sha256/sha256.h"
void qwen_native_stage(const char *);
void qwen_native_set_fault_report(const char *);
void qwen_native_log_bytes(const char *,std::size_t);
}
using Json=nlohmann::json;
using ModelFileIdentity=std::array<std::uint64_t,10>;
namespace qwen_app {
std::string sha256_metadata_bytes(const std::string &bytes) {
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,reinterpret_cast<const unsigned char*>(bytes.data()),bytes.size());
    unsigned char digest[32];sha256_final(&hash,digest);std::string result;
    for(auto v:digest){result+="0123456789abcdef"[v>>4];result+="0123456789abcdef"[v&15];}
    return result;
}
}
// Generated from the current complete application. No replacement shader
// admission, original-resource proof or identity implementation is introduced.
#include "isolated_PLE_boundaries.inc"
static void write_fresh_report(const std::string &path,const Json &value) {
    const auto raw=value.dump(2)+"\n";
    if(raw.size()>(1u<<20))throw std::runtime_error("Isolated PLE report exceeds its fixed cap");
    const int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    if(fd<0)throw std::runtime_error("Fresh isolated PLE report refused");
    const bool mode=!fchmod(fd,0644);
    const bool saved=mode&&write(fd,raw.data(),raw.size())==static_cast<ssize_t>(raw.size())&&!fsync(fd);
    const bool closed=!close(fd);
    if(!saved||!closed)throw std::runtime_error("Isolated PLE report persistence failed");
}
#include "isolated_PLE_admission.inc"
static Json source_identity_diagnostic(const std::string &path) {
    qwen_native_stage("PLE_source_metadata_open_before_GPU_not_started");
    const int fd=open(path.c_str(),O_RDONLY|O_NOFOLLOW);struct stat s{};
    const bool valid=fd>=0&&!fstat(fd,&s);const bool closed=fd>=0&&!close(fd);
    qwen_native_stage("PLE_source_metadata_calls_returned_GPU_not_started");
    if(!valid||!closed)throw std::runtime_error("PLE source diagnostic metadata refused");
    return {{"mode_bits",std::uint64_t(s.st_mode&07777)},{"inode_present",s.st_ino!=0},
        {"regular",bool(S_ISREG(s.st_mode))},{"bytes",std::uint64_t(s.st_size)},
        {"bounded_source_owner_eligible",bool(S_ISREG(s.st_mode)&&s.st_ino&&s.st_size>0&&!(s.st_mode&0022))}};
}
int main(int argc,char **argv) {
    bool resources=false;std::string report;Json snapshots=Json::array(),source_metadata=Json::object();
    const auto observe=[&](const char *phase){
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        const auto memory=qwen_app::observe_native_system_memory();
        snapshots.push_back({{"phase",phase},{"VM",diagnostic_VM_population()},
            {"CPU_heap_mapped_bytes",heap.mapped_bytes},{"CPU_heap_peak_bytes",heap.peak_bytes},
            {"CPU_heap_libc_fallbacks",heap.libc_fallbacks},{"Flexible_available_bytes",memory.flexible_available},
            {"kernel_free_pages",memory.kernel_free},{"kernel_startup_target_pages",memory.kernel_target}});
    };
    try {
        qwen_native_stage("isolated_PLE_main_entered_GPU_not_started");observe("main_entered");
        const auto startup=qwen_app::read_startup(argc,argv);report=startup.admission_report;
        qwen_native_set_fault_report((report+".fatal").c_str());
        llama_log_set(native_log,nullptr);ggml_log_set(native_log,nullptr);
        std::ifstream file(startup.development_policy);const auto policy=Json::parse(file);
        qwen_app::require_PLE_slice_policy(policy,startup.native_display);
        if(!startup.PLE_slice_validation||startup.clock_calibration||
           (!qwen_app::PLE_slice_smoke(policy)&&!qwen_app::PLE_slice_explicit_source(policy))||
           policy.at("console_operations_enabled")!=true||policy.at("console_validation_enabled")!=true||
           policy.at("allowed_modes")!=Json::array({"PLE-slice-validation"}))
            throw std::runtime_error("Isolated PLE title requires its exact headless smoke mode");
        const auto &binding=policy.at("native_isolated_PLE_title");
        if(!binding.is_object()||binding.size()!=6||binding.at("schema")!="ps5-qwen-isolated-PLE-title-v1"||
           binding.at("model_loading_enabled")!=false||binding.at("source_workers")!=0u||
           !binding.at("CPU_only_startup_calibration").is_boolean()||
           !binding.at("candidate_SELF_bytes").is_number_unsigned()||!binding.at("candidate_SELF_bytes").get<std::uint64_t>()||
           binding.at("candidate_SELF_bytes")>(32u<<20))
            throw std::runtime_error("Exact isolated PLE SELF and calibration scope required");
        qwen_app::enable_native_memory_backpressure();require_model_CPU_budget();
        qwen_app::verify_native_startup_file_direct("/app0/eboot.bin",binding.at("candidate_SELF_bytes").get<std::uint64_t>(),
            binding.at("candidate_SELF_sha256").get<std::string>(),30);
        qwen_native_stage("isolated_PLE_complete_SELF_SHA256_passed_GPU_not_started");observe("SELF_integrity_completed");
        qwen_app::admit_cpu_runtime(qwen_native_stage);qwen_app::inspect_vulkan_globals();
        qwen_native_stage("PLE_slice_before_shared_shader_CPU_admission GPU_not_started=1");
        admit_shader_storage_CPU(policy,report,true,Json(report));
        qwen_native_stage("PLE_slice_shared_shader_CPU_admission_completed GPU_not_started=1");observe("CPU_shader_completed");
        source_metadata["shader_resource"]=source_identity_diagnostic(policy.at("native_shader_storage").at("external_file").at("path").get<std::string>());
        if(qwen_app::PLE_slice_explicit_source(policy))source_metadata["qualified_source_guard"]=
            source_identity_diagnostic(policy.at("native_PLE_slice_validation").at("source_guard").at("path").get<std::string>());
        qwen_app::prepare_PLE_source_owner(policy);observe("CPU_source_owner_completed");
        if(binding.at("CPU_only_startup_calibration")==true) {
            const auto source=qwen_app::native_model_source_stats();
            write_fresh_report(report,{{"schema","ps5-qwen-isolated-PLE-CPU-calibration-v2"},{"pid",getpid()},
                {"observations",snapshots},{"GPU_initializations",0},{"GPU_graphs",0},{"model_loaded",false},
                {"source_identity_diagnostics",source_metadata},{"source_owner_prepared",true},
                {"source_preflight_read_calls",source.physical_read_calls},{"source_worker_read_ns",source.worker_read_ns},
                {"current_complete_source_SHA256_checked",qwen_app::PLE_slice_explicit_source(policy)},
                {"all_started_CPU_operations_returned",true},{"ordinary_OS_close_required",true}});
            qwen_native_stage("isolated_PLE_CPU_calibration_completed_waiting_for_ordinary_close_GPU_not_started");
            for(;;)(void)usleep(1000000);
        }
        (void)qwen_app::admit_native_startup_memory();
        std::int64_t physical=0;std::size_t available=0,flexible=0;const auto pool=sceKernelGetDirectMemorySize();
        if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&available)<0||
           sceKernelAvailableFlexibleMemorySize(&flexible)<0||available<(1ull<<30)||flexible<(64u<<20))
            throw std::runtime_error("Isolated PLE requires unchanged Direct and Flexible setup headroom");
        observe("before_GPU_initialization");resources=true;
        auto result=qwen_app::admit_PLE_slice_fixture(policy,report+".driver.log");qwen_native_driver_complete();
        const auto shaders=qwen_app::native_shader_asset_stats();
        if(!shaders.initialized||shaders.failed||shaders.active_lease||shaders.external_file.read_pending||
           !shaders.external_file.verified||shaders.CPU_verified_assets||shaders.decoded_calls+shaders.raw_calls==0||
           shaders.external_file.frame_requests!=shaders.decoded_calls+shaders.raw_calls)
            throw std::runtime_error("Isolated PLE shader use or retirement did not complete");
        observe("GPU_completed");
        result.update({{"pid",getpid()},{"positive_device_idle_and_epoch_retirement",true},
            {"shader_CPU_verified_assets",0u},{"shader_module_inputs_after_CPU_verification",shaders.decoded_calls+shaders.raw_calls},
            {"prior_all_shader_CPU_assets",shaders.assets},
            {"prior_all_shader_CPU_report_SHA256",policy.at("native_shader_storage").at("prior_native_CPU").at("report_sha256")},
            {"current_complete_external_file_SHA256_checked",true},{"all_used_shader_inputs_SHA256_checked",true},
            {"all_shader_input_leases_returned",true},{"isolated_title_memory_observations",snapshots},
            {"source_identity_diagnostics",source_metadata},
            {"Direct_available_before_GPU",available},{"Flexible_available_before_GPU",flexible}});
        write_fresh_report(report,result);
        qwen_native_stage("PLE_slice_validation_completed_waiting_for_ordinary_close model_loaded=0");
        for(;;)(void)usleep(1000000);
    }catch(const std::exception &error) {
        if(resources)qwen_native_driver_retain();
        qwen_native_stage("isolated_PLE_exception_after_work_stopped");
        if(!report.empty())try{write_fresh_report(report+".failure",{{"message",error.what()},
            {"native_GPU_resources_started",resources},{"observations",snapshots},{"source_identity_diagnostics",source_metadata},{"model_loaded",false}});}catch(...){}
        for(;;)(void)usleep(1000000);
    }
}
