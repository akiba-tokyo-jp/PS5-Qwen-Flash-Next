// SPDX-License-Identifier: MIT
// Independent CPU-only title. No inference engine, Vulkan, display or workers.
#include "shader_assets.h"
#include "shader_startup_memory_policy.h"
#include "stage_memory_probe.h"
#include "boundary_memory_trace.h"
#include "model_cpu_budget.h"
#include "system_memory.h"
#include "profile_clock.h"
#include "direct_integrity.h"
#include "startup.h"
#include <ps5platform/heap.h>
#include <nlohmann/json.hpp>
#include <array>
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
namespace qwen_app {
// The same pinned SHA256 implementation used by original metadata admission.
std::string sha256_metadata_bytes(const std::string &bytes) {
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,reinterpret_cast<const unsigned char*>(bytes.data()),bytes.size());
    unsigned char digest[32];sha256_final(&hash,digest);std::string result;
    for(auto v:digest){result+="0123456789abcdef"[v>>4];result+="0123456789abcdef"[v&15];}
    return result;
}
}
// The builder extracts these original helpers verbatim from native_main.cpp:
// boundary observations, original identity/prior proof, VM report and the
// shared shader admission. Their source hashes are frozen in the build receipt.
#include "mini_shader_boundaries.inc"
static void report_before(const char *phase){sample_boundary_memory(phase);}
static void report_after(const char *phase){sample_boundary_memory(phase);}
static void write_fresh_report(const std::string &path,const Json &value) {
    report_before("report_before_dump");const auto bytes=value.dump(2)+"\n";report_after("report_dump_returned");
    if(bytes.size()>(1u<<20))throw std::runtime_error("CPU shader report exceeds its fixed metadata cap");
    report_before("report_open_before_native_call");const int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    report_after("report_open_native_call_returned");if(fd<0)throw std::runtime_error("Fresh CPU shader report refused");
    report_before("report_mode_before_native_call");const int mode=fchmod(fd,0644);report_after("report_mode_native_call_returned");
    if(mode)throw std::runtime_error("CPU shader report mode refused");
    report_before("report_write_before_native_call");const auto got=write(fd,bytes.data(),bytes.size());report_after("report_write_native_call_returned");
    bool saved=got==static_cast<ssize_t>(bytes.size());
    if(saved){report_before("report_fsync_before_native_call");saved=!fsync(fd);report_after("report_fsync_native_call_returned");}
    report_before("report_close_before_native_call");const bool closed=!close(fd);report_after("report_close_native_call_returned");
    if(!saved||!closed)throw std::runtime_error("CPU shader report persistence refused");
}
static void require_model_CPU_budget() {
    sample_boundary_memory("CPU_work_guard_before");struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    if(heap.libc_fallbacks||heap.mapped_bytes>(16u<<20)||heap.peak_bytes>(16u<<20))
        throw std::runtime_error("Mini shader title exceeded its independently bounded Direct CPU heap");
    if(qwen_app::qualified_system_headroom(qwen_app::admit_native_system_memory())<(16u<<20))
        throw std::runtime_error("Mini shader title Flexible metadata reserve refused");
    sample_boundary_memory("CPU_work_guard_completed");
}
#include "mini_shader_admission.inc"
int main(int argc,char **argv) {
    qwen_native_stage("mini_shader_CPU_main_entered_GPU_not_started");
    try {
        const auto startup=qwen_app::read_startup(argc,argv);
        if(!startup.first_generation_validation||startup.native_display)
            throw std::runtime_error("Mini shader title requires the isolated headless first-generation transport");
        std::ifstream file(startup.development_policy);const auto policy=Json::parse(file);
        if(policy.at("console_operations_enabled")!=true||policy.at("native_mini_shader_title")!=Json({
            {"schema","ps5-qwen-mini-shader-title-v1"},{"CPU_only",true},{"maximum_SELF_bytes",4u<<20},
            {"maximum_CPU_heap_bytes",16u<<20},{"GPU_calls",0u},{"source_workers",0u},{"automatic_retries",0u}}))
            throw std::runtime_error("Exact mini shader CPU scope required");
        const auto &allowed=policy.at("allowed_modes");
        if(!allowed.is_array()||std::find(allowed.begin(),allowed.end(),Json("first-generation-validation"))==allowed.end())
            throw std::runtime_error("Mini shader transport mode disabled");
        qwen_app::require_shader_startup_memory_policy(policy);boundary_memory_enabled=true;
        const auto &gate=policy.at("native_first_generation_validation");const auto run=gate.at("run_id").get<std::string>();
        if(run.size()!=32||run.find_first_not_of("0123456789abcdef")!=std::string::npos||
           startup.admission_report!="/app0/qwen-runtime/plan-"+run+".json"||
           !gate.at("candidate_SELF_bytes").is_number_unsigned()||gate.at("candidate_SELF_bytes")>(4u<<20))
            throw std::runtime_error("Mini shader exact owner, output path and SELF bounds required");
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
        if(!qwen_app::begin_native_stage_memory_probe())throw std::runtime_error("Mini shader stage probe refused");
        admit_shader_storage_CPU(policy,startup.admission_report,true,run);
        if(!qwen_app::end_native_stage_memory_probe())throw std::runtime_error("Mini shader stage probe incomplete");
        const auto after=diagnostic_VM_population();Json samples=Json::array();
        for(std::size_t i=0;i<qwen_app::native_stage_memory_probe_count();++i) {
            const auto *s=qwen_app::native_stage_memory_probe_sample(i);
            if(!s||!s->valid)throw std::runtime_error("Mini shader stage sample invalid");
            samples.push_back({{"phase",s->phase},{"idle_before_ns",s->idle_before_ns},{"before_ns",s->before_ns},
                {"write_after_ns",s->write_after_ns},{"after_ns",s->after_ns},{"free_idle_before",s->free_idle_before},
                {"free_before",s->free_before},{"free_after_write",s->free_after_write},{"free_after",s->free_after},{"valid",true}});
        }
        const auto input=qwen_app::native_shader_file_stats();
        if(!input.verified||input.failed||input.read_pending)throw std::runtime_error("Mini shader input not positively returned");
        const auto operations=boundary_memory_report();
        write_fresh_report(startup.admission_report+".shader-startup-memory",{
            {"schema","ps5-qwen-shader-startup-memory-result-v1"},{"pid",getpid()},{"run_id",run},{"VM_before",before},{"VM_after",after},
            {"samples",samples},{"operation_boundaries",operations},{"matched_idle_ns",qwen_app::stage_memory_probe_idle_ns},
            {"shader_read_calls",input.read_calls},{"shader_returned_bytes",input.returned_bytes},{"shader_file_bytes",input.file_bytes},
            {"shader_input_window_bytes",input.input_window_bytes},{"all_shader_input_calls_returned",true},{"CPU_only",true},
            {"GPU_calls",0},{"source_workers",0},{"model_metadata_files",0},{"model_loaded",false},{"ordinary_OS_close_required",true}});
        qwen_native_stage("shader_startup_memory_CPU_completed_GPU_not_started_waiting_for_ordinary_close");
        for(;;)(void)usleep(1000000);
    }catch(...){qwen_native_stage("mini_shader_CPU_known_returned_refusal_GPU_not_started");qwen_native_halt("mini_shader_CPU_admission_refused");}
}
