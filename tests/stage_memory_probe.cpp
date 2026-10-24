// SPDX-License-Identifier: MIT
// Execute the actual bootstrap logger with deterministic I/O/counter failures.
#include <sys/types.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#ifndef O_NOFOLLOW
#define O_NOFOLLOW 0x100000
#endif
#ifndef F_DUPFD
#define F_DUPFD 3
#endif
static unsigned writes=0,syncs=0,queries=0;
static bool bad_query=false,short_write=false;
static std::uint32_t free_pages=5000;
static std::uint64_t ticks=0;
struct Halt{};
static int probe_open(const char *,int,...){static int next=3;return next++;}
static int probe_fchmod(int,int){return 0;}
static int probe_fcntl(int,int,...){return 5;}
static int probe_close(int){return 0;}
static int probe_getpid(){return 42;}
static ssize_t probe_write(int,const void *,std::size_t bytes){++writes;return ssize_t(bytes-(short_write?1:0));}
static int probe_fsync(int){++syncs;--free_pages;return 0;}
static int probe_sysctlbyname(const char *name,void *target,std::size_t *bytes,const void *,std::size_t){
    ++queries;if(std::strcmp(name,"vm.stats.vm0.v_free_count")||*bytes!=4)return -1;
    std::memcpy(target,&free_pages,4);if(bad_query)*bytes=8;return 0;
}
static int probe_clock_gettime(int,struct timespec *value){ticks+=1000;value->tv_sec=1;value->tv_nsec=long(ticks);return 0;}
extern "C" void qwen_native_set_fault_report(const char *){}
extern "C" void qwen_native_set_fault_journal(int){}
extern "C" [[noreturn]] void qwen_native_halt(const char *){throw Halt{};}
#define open probe_open
#define fchmod probe_fchmod
#define fcntl probe_fcntl
#define close probe_close
#define getpid probe_getpid
#define write probe_write
#define fsync probe_fsync
#define sysctlbyname probe_sysctlbyname
#define clock_gettime probe_clock_gettime
#include "../native/app/native_bootstrap.cpp"
#undef open
#undef fchmod
#undef fcntl
#undef close
#undef getpid
#undef write
#undef fsync
#undef sysctlbyname
#undef clock_gettime
static void check(bool ok,const char *message){if(!ok)throw std::runtime_error(message);}
int main(int argc,char **argv){try{
    check(argc==2,"Select a bootstrap diagnostic control");
    qwen_native_bootstrap();
    const auto before_queries=queries,before_writes=writes,before_syncs=syncs;
    qwen_native_stage("normal_stage");
    check(queries==before_queries&&writes==before_writes+2&&syncs==before_syncs+1,
        "Disabled probe changed actual durable journal behavior");
    using namespace qwen_app;
    check(begin_native_stage_memory_probe()&&!begin_native_stage_memory_probe(),"Probe reentry accepted");
    const std::string mode=argv[1];
    if(mode=="normal") {
        qwen_native_stage("model_mapping_before_open");
        check(end_native_stage_memory_probe()&&native_stage_memory_probe_count()==1,"Positive probe did not retire");
        const auto *sample=native_stage_memory_probe_sample(0);
        check(sample&&sample->valid&&sample->free_before==sample->free_after+1&&sample->after_ns>=sample->before_ns&&
            !std::strcmp(sample->phase,"model_mapping_before_open"),"Actual journal interval was not observed");
        check(!native_stage_memory_probe_sample(1)&&!begin_native_stage_memory_probe(),"One-shot ownership changed");
    } else if(mode=="capacity") {
        for(std::size_t i=0;i<=stage_memory_probe_capacity;++i)qwen_native_stage("bounded_sample");
        check(!end_native_stage_memory_probe()&&native_stage_memory_probe_count()==stage_memory_probe_capacity,
            "Overflow was reported complete or exceeded capacity");
        check(!native_stage_memory_probe_sample(stage_memory_probe_capacity),"Out-of-bounds sample exposed");
    } else if(mode=="counter_failure") {
        bad_query=true;qwen_native_stage("counter_failure");
        check(!end_native_stage_memory_probe(),"Malformed counter size reported complete");
        const auto *sample=native_stage_memory_probe_sample(0);check(sample&&!sample->valid,"Counter failure was hidden");
    } else if(mode=="short_write") {
        short_write=true;bool halted=false;try{qwen_native_stage("failed_journal");}catch(const Halt&){halted=true;}
        check(halted&&!end_native_stage_memory_probe()&&!native_stage_memory_probe_sample(0),
            "Failed durable journal or active sample was falsely retired");
    } else throw std::runtime_error("Unknown probe control");
    std::cout<<mode<<" actual bootstrap journal/probe control passed\n";
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
