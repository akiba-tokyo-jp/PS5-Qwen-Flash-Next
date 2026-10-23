// SPDX-License-Identifier: MIT
#pragma once
#include "../driver/arena.h"
#include <algorithm>
#include <cstdint>
#include <limits>
#include <stdexcept>
namespace qwen_app {
struct NativeAllocatorBudget {std::uint64_t pool=0,available=0,owned=0;};
inline NativeAllocatorBudget qualify_native_allocator_budget(std::uint64_t reported_total,
        std::uint64_t pool_first,std::uint64_t pool_last,std::uint64_t free_first,std::uint64_t free_last,
        const ps5_ai_arena_stats & before,const ps5_ai_arena_stats & after) {
    auto healthy=[](const ps5_ai_arena_stats & s) {
        return !s.mapping_uncertain&&!s.gpu_fault_retained&&!s.global_capacity_measured&&
            s.reserved_bytes==s.used_bytes&&s.physical_owned==bool(s.used_bytes)&&s.mapping_owned==bool(s.used_bytes);
    };
    if(!pool_first||pool_first>std::uint64_t(std::numeric_limits<std::int64_t>::max())||pool_first!=pool_last||reported_total!=pool_first||!free_first||!free_last||
       !healthy(before)||!healthy(after)||before.used_bytes!=after.used_bytes||
       before.allocation_attempts!=after.allocation_attempts||before.live_allocations!=after.live_allocations||
       before.used_bytes>pool_first||free_first>pool_first-before.used_bytes||free_last>pool_first-before.used_bytes)
        throw std::runtime_error("Stable native Direct allocator headroom is not admitted");
    // The canary-validated native query already excludes all allocated extents.
    // Never subtract owned bytes again or replace this with nominal pool minus use.
    return {pool_first,std::min(free_first,free_last),before.used_bytes};
}
}
