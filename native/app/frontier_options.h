// SPDX-License-Identifier: MIT
#pragma once
#include <atomic>
#include <cstdint>
namespace qwen_frontier {
// Scoped comparisons explicitly select these application-only experiments.
inline std::atomic<unsigned> mode{0};
inline std::uint64_t owner_stats[4]{};
inline std::uint64_t hc_stats[4]{};
}
