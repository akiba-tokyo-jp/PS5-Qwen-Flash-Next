// SPDX-License-Identifier: MIT
// Native adapter for the already checked paired Down Vulkan component.
#pragma once
#include <nlohmann/json.hpp>
#include <ps5platform/heap.h>
#include <ps5platform/kernel.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <fcntl.h>
#include <unistd.h>
#include <time.h>
#include <algorithm>
#include <array>
#include <cstdarg>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>
#include "native_gpu.h"
#include "driver_tables.h"
#include "resident_direct_tables.h"
#include "resident_incremental_tables.h"
#include "post_device_retirement.h"
#include "../driver/arena.h"
#include "../driver/journal_metrics.h"
extern "C" {
#include "sha256.h"
void qwen_native_stage(const char*);
[[noreturn]] void qwen_native_halt(const char*);
PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance,const char*);
int qwen_paired_digest(const char*,std::size_t,const char*);
extern int qwen_paired_journal;
extern uint32_t qwen_paired_minimum_free;
}
using NativeJson=nlohmann::json;
static NativeJson native_binding;
static std::string native_report;
static bool native_GPU_started=false;
static uint32_t native_main_free;
static void native_require(bool,const char*);
static uint32_t native_free_pages(){uint32_t value=0;std::size_t n=4;return !sysctlbyname("vm.stats.vm0.v_free_count",&value,&n,nullptr,0)&&n==4?value:0;}
static NativeJson native_Direct_readmission(){
    const uint64_t guard=0x5621a7865621a786ull;
    struct Output{uint64_t pre[2];int64_t start;size_t available;uint64_t post[2];};
    Output first{{guard,guard},-1,0,{guard,guard}},last=first;
    const auto total=sceKernelGetDirectMemorySize();
    native_require(total==12280922112ll,"Exact native Direct total required for CPU readmission");
    int a=sceKernelAvailableDirectMemorySize(0,total,65536,&first.start,&first.available);
    int b=sceKernelAvailableDirectMemorySize(0,total,65536,&last.start,&last.available);
    auto intact=[&](const Output&v){return v.pre[0]==guard&&v.pre[1]==guard&&v.post[0]==guard&&v.post[1]==guard&&
        v.start>=0&&uint64_t(v.start)<=uint64_t(total)&&v.available<=uint64_t(total)-uint64_t(v.start);};
    native_require(!a&&!b&&intact(first)&&intact(last)&&first.available>=12184453120ull&&last.available>=12184453120ull,
        "Native Direct capacity has not returned to the previously admitted baseline");
    return {{"completed",true},{"Direct_total_bytes",total},{"available_first",first.available},{"available_last",last.available},
        {"largest_start_first",first.start},{"largest_start_last",last.start},{"baseline_bytes",12184453120ull},
        {"canaries_exact",true},{"GPU_calls",0},{"individual_old_BO_release_claimed",false}};
}
#define native_journal qwen_paired_journal
static int unchanged(const struct stat*a,const struct stat*b){
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_size==b->st_size&&a->st_mode==b->st_mode&&
        a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&
        a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
#define QWEN_LAUNCH_WINDOW 65536u
alignas(16384) static unsigned char qwen_launch_window[QWEN_LAUNCH_WINDOW];
#define qwen_launch_digest_matches qwen_paired_digest
#include "paired_down_assets.h"
static void native_require(bool condition,const char*message){if(!condition)throw std::runtime_error(message);}
static void native_save(const std::string&path,NativeJson value){
    value["pid"]=getpid();value["run_id"]=native_binding.at("run_id");
    value["candidate_SELF_sha256"]=native_binding.at("SELF_sha256");
    const auto data=value.dump()+"\n";
    native_require(data.size()<=1u<<20,"Bounded native component report required");
    int fd=open(path.c_str(),O_WRONLY|O_CREAT|O_TRUNC|O_NOFOLLOW,0644);
    native_require(fd>=0,"Native component report open failed");
    bool ok=!fchmod(fd,0644)&&write(fd,data.data(),data.size())==ssize_t(data.size())&&!fsync(fd);
    int closed=close(fd);native_require(ok&&!closed,"Native component report did not return");
}
static void native_guard(unsigned extra=0){
    uint32_t free=0,minimum=0,reserved=0;
    const char*names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved"};
    uint32_t*values[]={&free,&minimum,&reserved};
    for(unsigned i=0;i<3;++i){std::size_t n=4;native_require(!sysctlbyname(names[i],values[i],&n,nullptr,0)&&n==4,"Native memory observation failed");}
    native_require(minimum==898&&reserved==206&&free>=std::uint64_t(minimum)+std::max(reserved,256u)+extra,"Native component memory predicate refused");
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    native_require(!heap.libc_fallbacks&&heap.peak_bytes<=64u<<20,"Native component tracked CPU heap limit refused");
    ps5_ai_arena_stats arena{};ps5_ai_arena_snapshot(&arena);
    native_require(!arena.mapping_uncertain&&!arena.gpu_fault_retained&&arena.peak_used_bytes<=128u<<20,"Native component owner limit refused");
}
static std::vector<unsigned char>native_read(const std::string&key){
    if(key=="CASES")return {paired_cases_json,paired_cases_json+sizeof(paired_cases_json)-1};
    const NativePart*part=nullptr;
    for(const auto&candidate:paired_parts)if(key==candidate.key){part=&candidate;break;}
    native_require(part&&part->bytes&&part->bytes<=16u<<20&&part->offset%16384==0&&
        part->offset<=paired_pack_bytes&&part->bytes<=paired_pack_bytes-part->offset,"Exact compiled component extent required");
    native_guard();
    int fd=open(paired_pack_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);native_require(fd>=0,"Native component input unavailable");
    struct stat before{},after{};
    native_require(!fstat(fd,&before)&&S_ISREG(before.st_mode)&&before.st_size==off_t(paired_pack_bytes)&&
        (before.st_mode&07777)==0444&&(fcntl(fd,F_GETFL)&O_DIRECT)==O_DIRECT,"Immutable native component descriptor required");
    std::vector<unsigned char>data(part->bytes);struct ai_sha256 hash;ai_sha256_init(&hash);
    for(std::uint64_t offset=0;offset<part->bytes;){
        native_guard();const auto logical=std::min<std::uint64_t>(part->bytes-offset,QWEN_LAUNCH_WINDOW);
        const auto count=(logical+16383)&~std::uint64_t(16383);
        auto got=pread(fd,qwen_launch_window,count,off_t(part->offset+offset));
        native_require(got==ssize_t(count),"Native component extent read did not return fully");
        ai_sha256_update(&hash,qwen_launch_window,logical);std::memcpy(data.data()+offset,qwen_launch_window,logical);offset+=logical;
    }
    native_require(!fstat(fd,&after)&&unchanged(&before,&after),"Native component descriptor changed");
    int closed=close(fd);native_require(!closed,"Native component descriptor close failed");
    unsigned char digest[32];char hex[65];ai_sha256_final(&hash,digest);
    for(unsigned i=0;i<32;++i)snprintf(hex+2*i,3,"%02x",digest[i]);
    native_require(!std::strcmp(hex,part->sha256),"Native component extent SHA256 differs");return data;
}
static void native_component_prepare(){
    native_guard(31);
    qwen_app::map_resident_driver_tables_to_Direct();
    const auto tables=qwen_app::restore_resident_tables_incrementally();
    const auto&backing=qwen_app::resident_direct_table_owner();
    native_require(tables.completed&&tables.tables==673&&tables.bytes==9471408&&backing.allocated&&backing.mapped&&backing.zeroed,
        "All original Direct tables must restore exactly before GPU initialization");
    void*first=nullptr;void*last=nullptr;uint32_t protection=0;
    native_require(!sceKernelQueryMemoryProtection(qwen_driver_table_storage.begin,&first,&last,&protection)&&
        uintptr_t(first)<=uintptr_t(qwen_driver_table_storage.begin)&&uintptr_t(last)>=uintptr_t(qwen_driver_table_storage.end)&&
        (protection&1)&&!(protection&2),"Original Direct table readonly protection required");
    native_save(native_report+".tables",{{"completed",true},{"tables",tables.tables},{"original_bytes",tables.bytes},
        {"same_VA",true},{"all_SHA256_passed",true},{"readonly",true},{"CPU_Direct_backing_retained_until_ordinary_close",true},
        {"GPU_calls",0},{"free_before",tables.before},{"free_after",tables.after}});
    native_guard(31);
    native_require(qwen_launch_digest_matches(paired_pack_path,paired_pack_bytes,paired_pack_sha256),"Complete native component pack SHA256/EOF refused");
    std::int64_t physical=0;std::size_t direct=0,flexible=0;const auto pool=sceKernelGetDirectMemorySize();
    native_require(pool>0&&!sceKernelAvailableDirectMemorySize(0,pool,65536,&physical,&direct)&&direct>=1ull<<30&&
        !sceKernelAvailableFlexibleMemorySize(&flexible)&&flexible>=64u<<20,"Native component Direct/Flexible admission refused");
    native_require(!setenv("MESA_SHADER_CACHE_DISABLE","true",1),"Disabled persistent shader caches required");
    native_GPU_started=true;qwen_native_gpu_initialize((native_report+".driver.log").c_str());qwen_native_driver_begin();
}
static uint64_t native_completed_epoch(){
    ps5_ai_arena_kick_stats kick{};
    native_require(!ps5_ai_arena_kick_snapshot(&kick)&&!kick.pending&&!kick.active&&!kick.submit_inflight&&
        !kick.fault_retained&&kick.log_healthy&&kick.requested_epoch==kick.completed_epoch&&
        kick.completed_epoch,"Positive native completion epoch required before device destruction");
    return kick.completed_epoch;
}
static void native_component_finish(uint64_t epoch){
    native_require(qwen_app::retire_destroyed_device(epoch,{ps5_ai_arena_kick_snapshot,ps5_ai_arena_snapshot,
        ps5_ai_driver_owner_ready,ps5_ai_driver_retire_quiet,ps5_ai_native_arena_journal_checkpoint}),
        "All native component owners must positively retire at the completed epoch");
    native_guard();
}
int qwen_paired_down_component(int,char**);
int main(){
    qwen_native_stage("paired_Down_native_main_entered_GPU_not_started");
    native_main_free=native_free_pages();
    try{
        alignas(16384) static char context[16384];
        native_guard();int fd=open("/app0/qwen-runtime/development.json",O_RDONLY|O_NOFOLLOW|O_DIRECT);
        native_require(fd>=0,"Native paired Down context unavailable");struct stat before{},after{};
        native_require(!fstat(fd,&before)&&before.st_size>0&&before.st_size<1024,"Bounded native paired Down context required");
        auto n=pread(fd,context,sizeof(context),0);bool stable=n==before.st_size&&!fstat(fd,&after)&&unchanged(&before,&after);
        int closed=close(fd);native_require(stable&&!closed,"Native paired Down context read failed");
        native_binding=NativeJson::parse(context,context+n);
        native_require(native_binding.size()==6&&native_binding.at("CPU_only").is_boolean()&&native_binding.at("schema")=="ps5-qwen-paired-Down-native-v1"&&
            native_binding.at("component_pack_sha256")==paired_pack_sha256,"Exact native paired Down scope required");
        const auto run=native_binding.at("run_id").get<std::string>(),sha=native_binding.at("SELF_sha256").get<std::string>();
        native_require(run.size()==32&&run.find_first_not_of("0123456789abcdef")==std::string::npos&&
            sha.size()==64&&sha.find_first_not_of("0123456789abcdef")==std::string::npos&&
            native_binding.at("SELF_bytes").get<std::uint64_t>()<=32u<<20,"Exact native paired Down identity required");
        native_report="/app0/qwen-runtime/plan-"+run+".json";
        native_save(native_report+".first.start",{{"completed",false},{"model_loads",0},{"GPU_started",false},{"VM_main_free",native_main_free}});
        native_journal=open((native_report+".IO").c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
        native_require(native_journal>=0&&!fchmod(native_journal,0644),"Fresh native paired Down I/O journal required");
        native_require(qwen_launch_digest_matches("/app0/eboot.bin",native_binding.at("SELF_bytes"),sha.c_str()),"Whole native paired Down SELF SHA256 refused");
        if(native_binding.at("CPU_only").get<bool>()){
            const auto capacity=native_Direct_readmission();
            native_require(!close(native_journal),"Native paired Down CPU journal close failed");native_journal=-1;
            struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
            native_save(native_report,{{"completed",true},{"CPU_only",true},{"all_CPU_IO_returned",true},{"SELF_verified",true},
                {"GPU_calls",0},{"model_loads",0},{"source_payload_reads",0},{"VM_main_free",native_main_free},
                {"VM_after_SELF_free",native_free_pages()},{"VM_minimum_SELF_free",qwen_paired_minimum_free},
                {"CPU_heap_peak_bytes",heap.peak_bytes},{"CPU_libc_fallbacks",heap.libc_fallbacks},{"Direct_readmission",capacity}});
            qwen_native_stage("paired_Down_native_CPU_returned_GPU_not_started_waiting_for_ordinary_close");
            for(;;)usleep(1000000);
        }
        char cases[]="CASES";char*args[]={cases,cases,const_cast<char*>(native_report.c_str())};
        int result=qwen_paired_down_component(3,args);
        native_require(!close(native_journal),"Native paired Down I/O journal close failed");native_journal=-1;
        native_require(result==0||result==2,"Native paired Down component result invalid");
        qwen_native_stage("paired_Down_native_GPU_completed_owners_retired_waiting_for_ordinary_close");
    }catch(const std::exception&error){
        if(native_GPU_started){qwen_native_driver_retain();qwen_native_halt("paired_Down_native_unknown_GPU_scope_retained");}
        if(native_journal>=0){if(close(native_journal))qwen_native_halt("paired_Down_native_CPU_close_unknown");native_journal=-1;}
        if(native_report.empty())qwen_native_halt("paired_Down_native_context_refused_before_binding");
        native_save(native_report+".failure",{{"completed",false},{"CPU_only",true},{"all_CPU_IO_returned",true},{"GPU_calls",0},{"model_loads",0},{"error",error.what()}});
        qwen_native_stage("paired_Down_native_CPU_returned_GPU_not_started_waiting_for_ordinary_close");
    }
    for(;;)usleep(1000000);
}
