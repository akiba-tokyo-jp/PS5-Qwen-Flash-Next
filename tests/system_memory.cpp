// SPDX-License-Identifier: MIT
#include "system_memory.h"
#include "memory_admission.h"
#include <sys/sysctl.h>
#include <ps5platform/kernel.h>
#include <cerrno>
#include <cstring>
#include <iostream>
#include <string>
using namespace qwen_app;
static std::string missing;
static bool bad_size=false,flexible_failure=false;
static unsigned free_calls=0;
static std::uint32_t first_free=1597,last_free=1600;
static void check(bool ok){if(!ok)throw std::runtime_error("System memory accounting invariant failed");}
template<class F>static void reject(F action){bool refused=false;try{action();}catch(const std::exception&){refused=true;}check(refused);}
int sysctlbyname(const char *name,void *target,std::size_t *bytes,void *,std::size_t){
    if(missing==name){errno=ENOENT;return -1;}
    std::uint32_t value=0;
    if(!std::strcmp(name,"hw.pagesize"))value=16384;
    else if(!std::strcmp(name,"vm.stats.vm0.v_page_count"))value=138739;
    else if(!std::strcmp(name,"vm.stats.vm0.v_free_min"))value=898;
    else if(!std::strcmp(name,"vm.stats.vm0.v_free_target"))value=2974;
    else if(!std::strcmp(name,"vm.stats.vm0.v_free_reserved"))value=206;
    else if(!std::strcmp(name,"vm.stats.vm0.v_free_count"))value=(free_calls++%2)?last_free:first_free;
    else throw std::runtime_error("An unqualified counter alias was queried");
    check(*bytes==4);std::memcpy(target,&value,4);*bytes=bad_size?8:4;return 0;
}
int sceKernelAvailableFlexibleMemorySize(std::size_t *bytes){*bytes=404750336;return flexible_failure?-1:0;}
int main(){
    auto s=observe_native_system_memory();check(free_calls==2&&s.kernel_free==1597);
    check(qualified_system_headroom(s)==404750336);
    // The actual I/O pre-snapshot is below this extra kernel margin: reject it
    // instead of counting its inactive pages or assuming future reclamation.
    s.kernel_free=1131;reject([&]{qualified_system_headroom(s);});
    bool pressure=false;try{qualified_system_headroom(s);}catch(const KernelMemoryPressure &){pressure=true;}
    check(pressure);
    s.kernel_free=1154;check(qualified_system_headroom(s)==404750336);
    --s.kernel_free;reject([&]{qualified_system_headroom(s);});
    for(const char *name:{"hw.pagesize","vm.stats.vm0.v_page_count","vm.stats.vm0.v_free_count",
        "vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_target","vm.stats.vm0.v_free_reserved"}){
        missing=name;reject([]{observe_native_system_memory();});
    }
    missing.clear();bad_size=true;reject([]{observe_native_system_memory();});bad_size=false;
    flexible_failure=true;reject([]{observe_native_system_memory();});flexible_failure=false;
    first_free=1700;last_free=1131;s=observe_native_system_memory();check(s.kernel_free==1131);reject([&]{qualified_system_headroom(s);});
    first_free=1597;last_free=1600;s=observe_native_system_memory();
    for(unsigned which=0;which<5;++which){auto bad=s;
        if(which==0)bad.page_size=4096;
        if(which==1)bad.kernel_reserved=bad.kernel_minimum+1;
        if(which==2)bad.kernel_target=bad.kernel_minimum;
        if(which==3)bad.kernel_free=bad.kernel_pages+1;
        if(which==4)bad.flexible_available=0;
        reject([&]{qualified_system_headroom(bad);});
    }
    ModelFootprint model;model.trunk_layers=48;model.mapped_files=360ull<<30;
    model.tensor("token_embd.weight",1ull<<30);model.tensor("per_layer_token_embd.weight",100ull<<30);
    model.tensor("blk.0.ffn_up_exps.weight",200ull<<30);model.tensor("blk.0.attn_q.weight",1ull<<30);
    MemoryBudget budget;budget.cpu_working=512ull<<20;
    MemoryObservation available{16ull<<30,16ull<<30,qualified_system_headroom(s),2ull<<30,256};
    // A 512 MiB CPU heap is charged to Direct; 386 MiB Flexible still preserves
    // its independent 256 MiB reserve. No physical pools are added together.
    budget.admit(model,available);
    available.flexible_available=budget.flexible_reserve-1;reject([&]{budget.admit(model,available);});
    available.flexible_available=budget.flexible_reserve;budget.admit(model,available);
    available.direct_largest=budget.device_requirement(model)-1;reject([&]{budget.admit(model,available);});
    std::cout<<"Separate Direct CPU/Flexible accounting, conservative kernel floor, unknown-counter rejection and bracketing passed; GPU_calls=0\n";
}
