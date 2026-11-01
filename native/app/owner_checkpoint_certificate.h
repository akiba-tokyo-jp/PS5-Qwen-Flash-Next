// SPDX-License-Identifier: MIT
#pragma once
#include "../driver/arena.h"
#include "../driver/journal_metrics.h"
#include <cstdint>
namespace qwen_frontier {
inline bool same_owner(const ps5_ai_arena_stats &a,const ps5_ai_arena_stats &b) {
    return a.reserved_bytes==b.reserved_bytes && a.used_bytes==b.used_bytes &&
        a.peak_used_bytes==b.peak_used_bytes && a.live_allocations==b.live_allocations &&
        a.allocation_attempts==b.allocation_attempts && a.denied_allocations==b.denied_allocations &&
        a.physical_owned==b.physical_owned && a.mapping_owned==b.mapping_owned &&
        a.mapping_uncertain==b.mapping_uncertain && a.gpu_fault_retained==b.gpu_fault_retained &&
        a.global_capacity_measured==b.global_capacity_measured;
}
inline bool same_journal(const ps5_ai_native_arena_journal_stats &a,const ps5_ai_native_arena_journal_stats &b) {
    return a.records && a.fsync_calls && a.log_healthy==1 && b.log_healthy==1 &&
        a.abi_bytes==sizeof(a) && b.abi_bytes==sizeof(b) && a.records==b.records &&
        a.checked_write_ns==b.checked_write_ns && a.fsync_calls==b.fsync_calls &&
        a.fsync_ns==b.fsync_ns && a.lock_wait_ns==b.lock_wait_ns;
}
struct OwnerCheckpointCertificate {
    const void *frontend=nullptr;
    std::uintptr_t device=0;
    std::uint64_t submitted=0,epoch=0;
    ps5_ai_arena_stats owner{};
    ps5_ai_native_arena_journal_stats journal{};
    bool matches(const void *f,std::uintptr_t d,std::uint64_t s,std::uint64_t e,
                 const ps5_ai_arena_stats &o,const ps5_ai_native_arena_journal_stats &j)const {
        // Allocation attempts prevent a free/reallocate ABA with equal byte/node totals.
        // All retirement, fresh owner checks and worker checks still run at every boundary.
        return frontend==f && d && device==d && s && submitted==s && e && epoch==e &&
            o.allocation_attempts!=UINT64_MAX && !o.mapping_uncertain && !o.gpu_fault_retained &&
            !o.global_capacity_measured && same_owner(owner,o) && same_journal(journal,j);
    }
};
}
