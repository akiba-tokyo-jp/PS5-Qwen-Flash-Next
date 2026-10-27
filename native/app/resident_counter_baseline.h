// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include <stdexcept>
namespace qwen_app {
// The patched expert counters are process-global atomics. A new context resets
// its slot maps and policy, not these counters. Preserve totals and price deltas.
inline void require_resident_context_counter_baseline(const ExpertCacheMetrics &before,
                                                       const ExpertCacheMetrics &after) {
    if(before.hits!=after.hits||before.misses!=after.misses||
       before.uploaded_bytes!=after.uploaded_bytes||before.prefetch_advice_bytes!=after.prefetch_advice_bytes)
        throw std::runtime_error("Unexpected expert transfer during completed context recreation");
}
}
