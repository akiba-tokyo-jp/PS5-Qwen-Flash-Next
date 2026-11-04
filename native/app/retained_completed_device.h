// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include "../driver/arena.h"
namespace qwen_app {
// A completed idle device remains explicitly owned until ordinary process close.
// This certificate never destroys a device or frees its driver backing.
struct RetainedCompletedDevice {
    std::uintptr_t device=0,instance=0;
    std::uint64_t epoch=0;
    ps5_ai_arena_stats owner{};
    bool held=false;
};
struct RetainedDeviceOps {
    int(*kick)(ps5_ai_arena_kick_stats*);
    void(*owner)(ps5_ai_arena_stats*);
    bool(*journal)();
};
inline bool retain_completed_device(std::uintptr_t device,std::uintptr_t instance,std::uint64_t epoch,
    RetainedCompletedDevice&lease,const RetainedDeviceOps&ops){
    if(!device||!instance||!epoch||lease.held||!ops.kick||!ops.owner||!ops.journal)return false;
    const auto quiet=[&]{ps5_ai_arena_kick_stats k{};
        return !ops.kick(&k)&&k.initialized&&k.thread_started&&!k.pending&&!k.active&&!k.submit_inflight&&
            !k.fault_retained&&k.log_healthy&&k.requested_epoch==epoch&&k.completed_epoch==epoch;};
    if(!quiet())return false;
    ps5_ai_arena_stats owner{};ops.owner(&owner);
    if(owner.mapping_uncertain||owner.gpu_fault_retained||owner.global_capacity_measured||owner.used_bytes>owner.reserved_bytes||
       (owner.mapping_owned&&!owner.physical_owned)||!ops.journal()||!quiet())return false;
    lease.device=device;lease.instance=instance;lease.epoch=epoch;lease.owner=owner;lease.held=true;
    return true;
}
}
