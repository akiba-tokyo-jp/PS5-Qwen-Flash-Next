// SPDX-License-Identifier: MIT
#include "memory_probe.h"
#include "virtual_source.h"
#include <ps5platform/kernel.h>
#include <ps5platform/heap.h>
#include <sys/sysctl.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <chrono>
#include <cstring>
#include <array>
extern "C" {
#include "hash/sha256/sha256.h"
}
extern "C" void qwen_native_stage(const char *);
namespace qwen_app {
namespace {
using Json=nlohmann::json;
Json counter(const char * name) {
    std::uint64_t value=0;std::size_t bytes=sizeof(value);errno=0;
    const int rc=sysctlbyname(name,&value,&bytes,nullptr,0);const int error=errno;
    const bool readable=rc==0 && (bytes==4 || bytes==8);
    return {{"readable",readable},{"rc",rc},{"errno",error},{"returned_bytes",bytes},
            {"value",readable ? Json(value) : Json(nullptr)}};
}
void stage(const char * text) {qwen_native_stage(text);}
std::string digest_bytes(const void * data,std::size_t bytes) {
    sha256_t hash;sha256_init(&hash);
    sha256_update(&hash,static_cast<const unsigned char *>(data),bytes);
    unsigned char sum[32];sha256_final(&hash,sum);std::string result;
    for(const auto byte:sum) {result+="0123456789abcdef"[byte>>4];result+="0123456789abcdef"[byte&15];}
    return result;
}
void headroom(const Json & s) {
    if(s.at("Direct_query_rc")!=0 || s.at("Flexible_query_rc")!=0 ||
       s.at("Direct_largest_available_bytes").get<std::uint64_t>()<(256u<<20) ||
       s.at("Flexible_available_bytes").get<std::uint64_t>()<(64u<<20) ||
       s.at("CPU_heap_mapped_bytes").get<std::uint64_t>()>(128u<<20) ||
       s.at("CPU_heap_libc_fallbacks")!=0)
        throw std::runtime_error("Native memory diagnostic headroom was not admitted");
}
Json direct_io(const Json & p) {
    constexpr std::size_t bytes=8u<<20;
    const auto path=p.at("fixture_path").get<std::string>();
    const auto digest=p.at("fixture_sha256").get<std::string>();
    if(path!="/app0/qwen-runtime/memory-probe.bin" || digest.size()!=64 ||
       digest.find_first_not_of("0123456789abcdef")!=std::string::npos)
        throw std::runtime_error("A fixed native direct-I/O fixture is required");
    const auto & prefixes=p.at("fixture_prefix_sha256");
    const std::array<std::size_t,4> sizes{16384,65536,1u<<20,bytes};
    if(!prefixes.is_object() || prefixes.size()!=sizes.size())
        throw std::runtime_error("Every direct-I/O window requires its own prefix SHA256");
    for(const auto count:sizes) {
        const auto & value=prefixes.at(std::to_string(count));
        if(!value.is_string())throw std::runtime_error("Direct-I/O prefix SHA256 must be a string");
        const auto text=value.get<std::string>();
        if(text.size()!=64 || text.find_first_not_of("0123456789abcdef")!=std::string::npos)
            throw std::runtime_error("Invalid direct-I/O prefix SHA256");
    }
    if(prefixes.at(std::to_string(bytes))!=digest)
        throw std::runtime_error("Full fixture and final prefix SHA256 must match");
    stage("memory_direct_io_before_open GPU_not_started=1 model_loaded=0");
    const int fd=open(path.c_str(),O_RDONLY|O_DIRECT|O_NOFOLLOW);
    stage("memory_direct_io_open_returned GPU_not_started=1 model_loaded=0");
    if(fd<0) throw std::runtime_error("Native direct-I/O fixture open failed");
    struct stat before{};
    if(fstat(fd,&before) || !S_ISREG(before.st_mode) || before.st_uid || before.st_gid ||
       (before.st_mode&0777)!=0644 || before.st_size!=bytes) {
        close(fd);throw std::runtime_error("Native direct-I/O fixture identity rejected");
    }
    stage("memory_direct_io_before_bounded_heap_allocation bytes=8388608");
    void * buffer=ps5_heap_memalign(16384,bytes);
    stage("memory_direct_io_bounded_heap_allocation_returned");
    if(!buffer) {close(fd);throw std::runtime_error("Bounded Direct heap allocation refused");}
    Json windows=Json::array();bool completed=true;std::string actual;
    const auto started=std::chrono::steady_clock::now();
    for(const std::size_t count : sizes) {
        headroom(observe_native_memory());
        if(std::chrono::steady_clock::now()-started>std::chrono::seconds(30)) {completed=false;break;}
        const auto mark="memory_direct_io_before_pread bytes="+std::to_string(count);
        stage(mark.c_str());
        const auto got=pread(fd,buffer,count,0);
        stage("memory_direct_io_pread_returned");
        if(got!=static_cast<ssize_t>(count)) {completed=false;break;}
        actual=digest_bytes(buffer,count);
        if(actual!=prefixes.at(std::to_string(count))) {completed=false;break;}
        windows.push_back(count);
    }
    struct stat after{};const bool stable=fstat(fd,&after)==0 &&
        before.st_dev==after.st_dev && before.st_ino==after.st_ino && before.st_size==after.st_size &&
        before.st_mode==after.st_mode && before.st_uid==after.st_uid && before.st_gid==after.st_gid &&
        before.st_mtim.tv_sec==after.st_mtim.tv_sec && before.st_mtim.tv_nsec==after.st_mtim.tv_nsec &&
        before.st_ctim.tv_sec==after.st_ctim.tv_sec && before.st_ctim.tv_nsec==after.st_ctim.tv_nsec;
    // pread has returned before these CPU-owned resources are retired. No
    // timeout outside pread can cancel it; no speculative cleanup is attempted.
    ps5_heap_free(buffer);const bool closed=close(fd)==0;
    stage("memory_direct_io_buffer_freed_and_file_close_returned");
    if(!completed || !stable || !closed || actual!=digest)
        throw std::runtime_error("Native direct-I/O completion, identity or SHA256 failed");
    return {{"windows_completed_bytes",windows},{"fixture_SHA256_matched",true},
            {"all_prefix_SHA256_matched",true},{"file_closed",true},{"CPU_buffer_freed",true},{"maximum_window_bytes",bytes}};
}
}
Json observe_native_memory() {
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    const auto pool=sceKernelGetDirectMemorySize();std::int64_t physical=0;
    std::size_t available=0,flexible=0;
    stage("memory_telemetry_before_Direct_query GPU_not_started=1 model_loaded=0");
    const int direct_rc=pool>0 ? sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&available) : -1;
    stage("memory_telemetry_Direct_query_returned");
    const int flexible_rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    stage("memory_telemetry_Flexible_query_returned");
    Json counters=Json::object();
    for(const char * name : {"hw.pagesize","vm.stats.vm.v_free_count","vm.stats.vm.v_page_size",
        "vm.stats.vm0.v_page_count","vm.stats.vm0.v_free_count","vm.stats.vm0.v_inactive_count",
        "vm.stats.vm0.v_active_count","vm.stats.vm0.v_wire_count","vm.stats.vm0.v_free_min",
        "vm.stats.vm0.v_free_target","vm.stats.vm0.v_free_reserved"}) counters[name]=counter(name);
    return {{"Direct_pool_bytes",pool},{"Direct_query_rc",direct_rc},
        {"Direct_largest_available_bytes",direct_rc==0 ? available : 0},
        {"Flexible_query_rc",flexible_rc},{"Flexible_available_bytes",flexible_rc==0 ? flexible : 0},
        {"CPU_heap_mapped_bytes",heap.mapped_bytes},{"CPU_heap_peak_bytes",heap.peak_bytes},
        {"CPU_heap_libc_fallbacks",heap.libc_fallbacks},{"CPU_heap_segments",heap.segments},
        {"raw_kernel_counters",counters},{"CPU_heap_uses_Direct_pool",true},
        {"vm0_process_available_RAM_qualified",false},{"full_model_memory_admitted",false}};
}
Json run_native_memory_probe(const Json & policy) {
    const auto & p=policy.at("native_memory_validation");const auto phase=require_memory_probe_policy(policy,false);
    Json result{{"phase",phase},{"before",observe_native_memory()},
        {"virtual_bytes_reserved",0},{"file_mmap_calls",0},{"model_loaded",false},
        {"Vulkan_initialized",false},{"GPU_calls",0},{"full_model_memory_admitted",false}};
    // The complete pre-operation snapshot is already persisted separately.
    // Keep journal lines below the bootstrap's fixed 1024-byte bound.
    stage("memory_telemetry_snapshot_complete GPU_not_started=1 model_loaded=0");
    if(phase=="virtual-16KiB") {
        headroom(result.at("before"));
        const auto at=reserve_native_virtual_source(16384);
        stage("memory_virtual_16KiB_reserved_and_protection_zero_verified");
        release_native_virtual_source(at,16384);
        stage("memory_virtual_16KiB_release_completed");
        result["virtual_bytes_reserved"]=16384;result["virtual_release_completed"]=true;
    } else if(phase=="direct-io") {
        headroom(result.at("before"));result["direct_io"]=direct_io(p);
    }
    result["after"]=observe_native_memory();result["completed"]=true;return result;
}
}
