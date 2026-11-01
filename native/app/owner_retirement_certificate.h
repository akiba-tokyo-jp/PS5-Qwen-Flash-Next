// SPDX-License-Identifier: MIT
#pragma once
#include "owner_checkpoint_certificate.h"
namespace qwen_throughput {
struct OwnerRetirementCertificate {
    const void *frontend=nullptr;
    std::uintptr_t device=0;
    std::uint64_t submitted=0,epoch=0;
    ps5_ai_arena_stats owner{};
    bool matches(const void*f,std::uintptr_t d,std::uint64_t s,std::uint64_t e,
                 const ps5_ai_arena_stats&o)const {
        // This certificate is published only after the original retirement walk
        // drains every retired node. Without a new allocation attempt, any new
        // LIVE -> RETIRED transition strictly decreases the live count. An
        // unchanged full snapshot therefore cannot hide a new retired node.
        // Queue exclusion, fresh worker/health checks and positive completion
        // are obligations of the caller at every use, including newer epochs.
        return frontend==f&&d&&device==d&&s&&s>=submitted&&e&&e>=epoch&&
            owner.allocation_attempts!=UINT64_MAX&&o.allocation_attempts!=UINT64_MAX&&
            !o.mapping_uncertain&&!o.gpu_fault_retained&&!o.global_capacity_measured&&
            qwen_frontier::same_owner(owner,o);
    }
};
}
