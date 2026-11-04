// SPDX-License-Identifier: MIT
#pragma once
#include "../driver/arena.h"
namespace qwen_app {
struct PostDeviceRetirement {
    int (*kick)(ps5_ai_arena_kick_stats*);
    void (*owner)(ps5_ai_arena_stats*);
    int (*ready)();
    int (*retire)(uint64_t);
    bool (*journal)();
};
// The same sole frontend first completes work while the VkDevice is valid.
// Device destruction may retire additional BOs. Drain those at the SAME
// already completed epoch without ever calling DeviceWaitIdle on a dead handle.
inline bool retire_destroyed_device(uint64_t epoch,const PostDeviceRetirement&ops){
    if(!epoch||!ops.kick||!ops.owner||!ops.ready||!ops.retire||!ops.journal)return false;
    auto quiet=[&]{ps5_ai_arena_kick_stats k{};return !ops.kick(&k)&&k.initialized&&k.thread_started&&
        !k.pending&&!k.active&&!k.submit_inflight&&!k.fault_retained&&k.log_healthy&&
        k.requested_epoch==epoch&&k.completed_epoch==epoch&&ops.ready();};
    if(!quiet()||ops.retire(epoch)!=1||!quiet())return false;
    ps5_ai_arena_stats owner{};ops.owner(&owner);
    return !owner.used_bytes&&!owner.reserved_bytes&&!owner.live_allocations&&!owner.physical_owned&&
        !owner.mapping_owned&&!owner.mapping_uncertain&&!owner.gpu_fault_retained&&
        !owner.global_capacity_measured&&ops.journal();
}
}
