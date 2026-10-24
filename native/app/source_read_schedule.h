// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>

namespace qwen_app {
inline constexpr std::uint64_t source_schedule_region_bytes = 1ull << 30;
inline constexpr std::uint64_t source_schedule_boundary_margin = 4ull << 20;

// An empirical candidate restriction, not a claim about the closed BFS layout.
// Both complete aligned extents must remain inside one conservatively inset region.
inline bool source_schedule_extent(std::uint64_t offset, std::uint64_t bytes,
        const std::array<std::uint64_t, 10> & identity) {
    if (!identity[0] || !identity[1] || !bytes || offset >= identity[5] || bytes > identity[5] - offset)
        return false;
    const auto within = offset % source_schedule_region_bytes;
    return within >= source_schedule_boundary_margin &&
        within <= source_schedule_region_bytes - source_schedule_boundary_margin &&
        bytes <= source_schedule_region_bytes - source_schedule_boundary_margin - within;
}

inline bool source_schedule_parallel(const std::array<std::uint64_t, 10> & first,
        std::uint64_t offset0, std::uint64_t bytes0, const std::array<std::uint64_t, 10> & second,
        std::uint64_t offset1, std::uint64_t bytes1) {
    if (!source_schedule_extent(offset0, bytes0, first) || !source_schedule_extent(offset1, bytes1, second))
        return false;
    if (first[0] != second[0]) return false;
    return first[1] != second[1] ||
        offset0 / source_schedule_region_bytes == offset1 / source_schedule_region_bytes;
}
}
