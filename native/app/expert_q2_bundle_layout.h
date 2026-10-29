// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// Compact arithmetic index. No per-Expert virtual mapping range is added.
struct ExpertQ2BundleLayout {
    static constexpr std::uint64_t alignment=16384,part_limit=512ull<<20;
    static constexpr std::array<std::uint64_t,3> role_bytes{537600,537600,460800};
    static constexpr std::array<std::uint64_t,3> role_offsets{0,537600,1075200};
    static constexpr std::uint64_t payload_bytes=1536000,stride=1540096;
    static constexpr unsigned layers=49,experts=512,bundles_per_part=unsigned(part_limit/stride),parts_per_layer=2;
    struct Location {unsigned part;std::uint64_t offset,bytes;};
    static Location locate(unsigned layer,unsigned expert) {
        if(layer>=layers||expert>=experts)throw std::out_of_range("Original layer/Expert required");
        return {layer*parts_per_layer+expert/bundles_per_part,(expert%bundles_per_part)*stride,stride};
    }
    static std::uint64_t part_bytes(unsigned part) {
        if(part>=layers*parts_per_layer)throw std::out_of_range("Original bundle part required");
        const unsigned first=(part%parts_per_layer)*bundles_per_part;
        return std::uint64_t(experts-first<bundles_per_part?experts-first:bundles_per_part)*stride;
    }
    static std::uint64_t role_offset(unsigned role) {
        if(role>=role_offsets.size())throw std::out_of_range("Original Expert role required");
        return role_offsets[role];
    }
};
}
