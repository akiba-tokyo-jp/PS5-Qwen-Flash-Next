// SPDX-License-Identifier: MIT
// Exercise the actual native diagnostic with injected public APIs and failures.
#include "memory_probe.h"
#include "source_virtual_addresses.h"
#include "virtual_source.h"
#include <ps5platform/kernel.h>
#include <ps5platform/heap.h>
#include <sys/stat.h>
#include <sys/resource.h>
#include <fcntl.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <iostream>
#include <fstream>
#include <vector>
#include <utility>
#include <string>
#include <malloc.h>
extern "C" {
#include "hash/sha256/sha256.h"
}
using Json=nlohmann::json;
static unsigned reservations=0,queries=0,releases=0,opens=0,reads=0,closes=0,frees=0;
static bool low_memory=false,bad_protection=false,bad_release=false,short_read=false;
static bool unknown_limit=false;
static bool bad_reservation=false,wrong_address=false;
static std::size_t longest_stage=0;
static void check(bool value) {if(!value)throw std::runtime_error("Native memory invariant failed");}
template<class F> static void reject(F action) {bool refused=false;try{action();}catch(const std::exception&){refused=true;}check(refused);}
extern "C" void qwen_native_stage(const char * text) {
    const auto bytes=std::strlen(text);check(bytes<=1024);longest_stage=std::max(longest_stage,bytes);
}
std::int64_t sceKernelGetDirectMemorySize(){return 12ull<<30;}
int sceKernelAvailableDirectMemorySize(std::int64_t,std::int64_t,std::size_t,std::int64_t *p,std::size_t *n){*p=0;*n=low_memory?64ull<<20:11ull<<30;return 0;}
int sceKernelAvailableFlexibleMemorySize(std::size_t *n){*n=256u<<20;return 0;}
void ps5_heap_stats(struct ps5_heap_stats *s){*s={32u<<20,32u<<20,1,0,0x2000000000ull,16ull<<30};}
extern "C" int getrlimit(int kind,struct rlimit *value){
    check(kind==RLIMIT_AS||kind==RLIMIT_DATA);
    if(unknown_limit){errno=EINVAL;return -1;}
    value->rlim_cur=1ull<<45;value->rlim_max=~std::uint64_t(0);return 0;
}
void *ps5_heap_memalign(std::size_t alignment,std::size_t bytes){check(alignment==16384&&bytes==(8u<<20));return _aligned_malloc(bytes,alignment);}
void ps5_heap_free(void *p){++frees;_aligned_free(p);}
int sysctlbyname(const char *name,void *p,std::size_t *bytes,void *,std::size_t){
    if(std::strstr(name,"vm.stats.vm.")){errno=ENOENT;return -1;}
    const std::uint32_t value=std::strcmp(name,"hw.pagesize")==0?16384:1000;
    check(*bytes>=sizeof(value));std::memcpy(p,&value,sizeof(value));*bytes=sizeof(value);return 0;
}
int sceKernelReserveVirtualRange(void **p,std::size_t bytes,int flags,std::size_t align){
    check(bytes==16384&&flags==0x90&&align==16384&&reinterpret_cast<std::uintptr_t>(*p)==qwen_app::source_key_base);
    ++reservations;if(wrong_address)*p=reinterpret_cast<void *>(qwen_app::source_key_base+16384);
    return bad_reservation?-2147352564:0;
}
int sceKernelQueryMemoryProtection(void *p,void **first,void **last,std::uint32_t *bits){++queries;*first=p;*last=reinterpret_cast<void *>(reinterpret_cast<std::uintptr_t>(p)+16384);*bits=bad_protection?1:0;return 0;}
int sceKernelMunmap(void *,std::size_t bytes){check(bytes==16384);++releases;return bad_release?-1:0;}
int memory_probe_test_open(const char *path,int flags){check(std::strcmp(path,"/app0/qwen-runtime/memory-probe.bin")==0&&flags==(O_RDONLY|O_DIRECT|O_NOFOLLOW));++opens;return 7;}
int memory_probe_test_fstat(int fd,struct stat *s){check(fd==7);*s={1,2,8u<<20,0100644,0,0,{1,2},{3,4}};return 0;}
int memory_probe_test_close(int fd){check(fd==7);++closes;return 0;}
ssize_t memory_probe_test_pread(int fd,void *p,std::size_t bytes,std::int64_t at){
    check(fd==7&&at==0&&bytes<=(8u<<20)&&bytes%16384==0);++reads;
    std::memset(p,0x42,bytes);return short_read?bytes-1:bytes;
}
static Json policy(const char *phase) {
    return {{"native_memory_validation",{{"schema","ps5-qwen-native-memory-validation-v1"},
        {"phase",phase},{"fresh_idle_session_bound_by_launcher",true},
        {"original_numerical_readmission_passed_this_boot",true},{"model_loading_enabled",false},
        {"Vulkan_initialization_enabled",false},{"maximum_virtual_probe_bytes",16384u},
        {"maximum_io_window_bytes",8u<<20},{"preceding_telemetry_and_normal_close_passed_this_boot",true},
        {"preceding_virtual_probe_and_normal_close_passed_this_boot",true}}}};
}
int main(int argc,char **argv) {
    if(argc==2) {
        const std::string kind=argv[1];
        bad_protection=kind=="bad-protection";bad_release=kind=="bad-release";
        bad_reservation=kind=="bad-reservation";wrong_address=kind=="wrong-address";
        check(bad_protection||bad_release||bad_reservation||wrong_address);
        reject([]{qwen_app::run_native_memory_probe(policy("virtual-16KiB"));});
        check(reservations==1&&queries==(bad_reservation||wrong_address?0u:1u)&&releases==(bad_release?1u:0u));
        reject([]{qwen_app::run_native_memory_probe(policy("virtual-16KiB"));});check(reservations==1);
        std::cout<<"Failed native address operation retained without retry or speculative release: "<<kind<<'\n';return 0;
    }
    if(argc==3) {
        check(std::string(argv[1])=="model-spans");
        std::ifstream stream(argv[2]);Json receipt;stream>>receipt;
        qwen_app::SourceVirtualAddresses plan;std::vector<std::pair<std::uintptr_t,std::size_t>> live;
        std::uint64_t total=0;
        for(const auto & file:receipt.at("files")) {
            const auto bytes=qwen_app::virtual_source_span(file.at("bytes").get<std::uint64_t>());
            const auto at=plan.claim(bytes);check(at>=qwen_app::source_key_base&&at+bytes<=qwen_app::source_key_base+qwen_app::source_key_bytes);
            for(const auto & previous:live)check(at>=previous.first+previous.second||previous.first>=at+bytes);
            live.emplace_back(at,bytes);total+=file.at("bytes").get<std::uint64_t>();
        }
        check(live.size()==76&&total==359246956672ull);
        for(auto i=live.rbegin();i!=live.rend();++i)plan.retire(i->first,i->second);
        check(plan.claim(16384)==qwen_app::source_key_base);plan.retire(qwen_app::source_key_base,16384);
        reject([&]{plan.retire(qwen_app::source_key_base,16384);});
        const auto whole=plan.claim(qwen_app::source_key_bytes);reject([&]{plan.claim(16384);});
        plan.retire(whole,qwen_app::source_key_bytes);
        const auto a=plan.claim(16384),b=plan.claim(32768),c=plan.claim(16384);
        plan.retire(b,32768);check(plan.claim(32768)==b);plan.retire(a,16384);plan.retire(c,16384);
        plan.retain();reject([&]{plan.claim(16384);});
        std::cout<<"All 76 real model spans fit disjoint addresses; full reuse, fragmentation, exhaustion and retained-state checks passed\n";return 0;
    }
    auto result=qwen_app::run_native_memory_probe(policy("telemetry"));
    check(result["completed"]==true&&reservations==0&&opens==0&&reads==0);
    check(result["before"]["raw_kernel_counters"]["vm.stats.vm.v_free_count"]["readable"]==false);
    check(result["before"]["process_limits"]["RLIMIT_AS"]["soft_bytes"]==(1ull<<45));
    check(result["before"]["process_limits"]["RLIMIT_DATA"]["hard_bytes"]==~std::uint64_t(0));
    check(result["before"]["CPU_heap_range_base"]==0x2000000000ull);
    unknown_limit=true;auto unknown=qwen_app::observe_native_memory();unknown_limit=false;
    check(unknown["process_limits"]["RLIMIT_AS"]["readable"]==false);
    check(unknown["process_limits"]["RLIMIT_AS"]["soft_bytes"].is_null());
    check(result["before"].dump().size()>1024); // Regression: never place this whole JSON in a journal line.
    result=qwen_app::run_native_memory_probe(policy("virtual-16KiB"));
    check(result["virtual_release_completed"]==true&&reservations==1&&queries==1&&releases==1);
    low_memory=true;reject([]{qwen_app::run_native_memory_probe(policy("virtual-16KiB"));});check(reservations==1);low_memory=false;
    auto io=policy("direct-io");io["native_memory_validation"]["fixture_path"]="/app0/qwen-runtime/memory-probe.bin";
    const std::string fixture(8u<<20,0x42);sha256_t hash;sha256_init(&hash);
    sha256_update(&hash,reinterpret_cast<const unsigned char *>(fixture.data()),fixture.size());
    unsigned char digest[32];sha256_final(&hash,digest);std::string hex;
    for(const auto value:digest){hex+="0123456789abcdef"[value>>4];hex+="0123456789abcdef"[value&15];}
    io["native_memory_validation"]["fixture_sha256"]=hex;
    for(const unsigned count:{16384u,65536u,1u<<20,8u<<20}) {
        sha256_init(&hash);sha256_update(&hash,reinterpret_cast<const unsigned char *>(fixture.data()),count);
        sha256_final(&hash,digest);std::string prefix;
        for(const auto value:digest){prefix+="0123456789abcdef"[value>>4];prefix+="0123456789abcdef"[value&15];}
        io["native_memory_validation"]["fixture_prefix_sha256"][std::to_string(count)]=prefix;
    }
    result=qwen_app::run_native_memory_probe(io);check(result["direct_io"]["fixture_SHA256_matched"]==true);
    check(reads==4&&frees==1&&closes==1);
    short_read=true;reject([&]{qwen_app::run_native_memory_probe(io);});check(reads==5&&frees==2&&closes==2);
    short_read=false;
    io["native_memory_validation"]["fixture_prefix_sha256"]["16384"]=std::string(64,'0');
    reject([&]{qwen_app::run_native_memory_probe(io);});check(reads==6&&frees==3&&closes==3);
    io["native_memory_validation"]["fixture_prefix_sha256"].erase("65536");
    reject([&]{qwen_app::run_native_memory_probe(io);});check(opens==3);
    check(longest_stage<=1024);
    std::cout<<"Actual native memory diagnostic passed: bounded journal, raw telemetry, tiny reservation, no speculative release, direct I/O and short-read retirement; GPU_calls=0\n";
}
