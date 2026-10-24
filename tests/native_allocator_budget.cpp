// SPDX-License-Identifier: MIT
#include "native_gpu.h"
#include <array>
#include <iostream>
#include <limits>
#include <cstring>
using Stats=ps5_ai_arena_stats;
static constexpr std::uint64_t pool=12280922112ull;
static std::array<Stats,2> states;
static std::array<std::uint64_t,2> pools,available;
static std::array<bool,2> ready;
static unsigned snapshots,pool_calls,free_calls,ready_calls,checks;
static void check(bool value){if(!value)throw std::runtime_error("Actual native allocator budget invariant failed");}
extern "C" int ps5_ai_driver_owner_ready(){check(ready_calls<2);return ready[ready_calls++];}
extern "C" void ps5_ai_arena_snapshot(Stats *s){check(snapshots<2);*s=states[snapshots++];}
extern "C" std::uint64_t radv_ps5_memory_pool_bytes(){check(pool_calls<2);return pools[pool_calls++];}
extern "C" std::uint64_t radv_ps5_memory_available_bytes(){check(free_calls<2);return available[free_calls++];}
extern "C" void qwen_native_stage(const char *text){check(std::strlen(text)<=1024);}
#include "actual_native_allocator_budget.h"
static void reset(std::uint64_t owned=8755384320ull){
    snapshots=pool_calls=free_calls=ready_calls=0;states={};
    states[0].used_bytes=states[0].reserved_bytes=owned;
    states[0].live_allocations=owned?7:0;states[0].allocation_attempts=owned?7:0;
    states[0].physical_owned=states[0].mapping_owned=bool(owned);states[1]=states[0];
    pools={pool,pool};available={pool-owned-(64u<<20),pool-owned-(64u<<20)-16384};ready={true,true};
}
template<class F>static void reject(F mutate,std::uint64_t reported=pool){
    reset();mutate();bool refused=false;
    try{(void)qwen_native_allocator_budget(reported);}catch(const std::exception&){refused=true;}
    check(refused);++checks;
}
int main(){
    for(const auto owned:{0ull,32ull<<20,pool/4,pool/2,8755384320ull,pool-(256ull<<20)}){
        reset(owned);const auto actual=qwen_native_allocator_budget(pool);
        check(actual.available==available[1]&&actual.owned==owned&&actual.pool==pool);
        check(snapshots==2&&pool_calls==2&&free_calls==2&&ready_calls==2);++checks;
    }
    reset();const auto actual=qwen_native_allocator_budget(pool);
    check(actual.available>(1920ull<<20)&&actual.available<pool-actual.owned);++checks;
    reject([]{ready[0]=false;});check(snapshots==0&&pool_calls==0&&free_calls==0);
    reject([]{ready[1]=false;});
    reject([]{pools[0]=0;});reject([]{pools[1]-=16384;});reject([]{},pool-16384);
    reject([]{available[0]=0;});reject([]{available[1]=0;});
    reject([]{available[0]=pool;});reject([]{available[1]=pool;});
    reject([]{states[0].mapping_uncertain=1;});reject([]{states[1].mapping_uncertain=1;});
    reject([]{states[0].gpu_fault_retained=1;});reject([]{states[1].gpu_fault_retained=1;});
    reject([]{states[0].global_capacity_measured=1;});
    reject([]{states[1].used_bytes-=16384;states[1].reserved_bytes=states[1].used_bytes;});
    reject([]{++states[1].allocation_attempts;});reject([]{++states[1].live_allocations;});
    reject([]{states[1].mapping_owned=0;});reject([]{states[1].physical_owned=0;});
    reject([]{++states[0].reserved_bytes;});
    reject([]{states[0].used_bytes=states[0].reserved_bytes=pool+16384;states[1]=states[0];});
    reject([]{pools={~std::uint64_t(0),~std::uint64_t(0)};},~std::uint64_t(0));
    std::cout<<"Actual native allocator observation: "<<checks<<" lower-sample, pool/owner, fragmentation, concurrent-change, zero-query and retained-fault checks passed; no allocation/GPU calls\n";
}
