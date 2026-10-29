// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace qwen_app {
// A complete logical GGUF is assembled from immutable physical byte ranges.
// Sparse zero placeholders are never returned for an aliased tensor payload.
struct ExpertQ2SourceSegment {
    std::uint64_t logical_offset,bytes;
    std::size_t physical;
    std::uint64_t physical_offset;
};
struct ExpertQ2SourceSegments {
    std::string path;
    std::vector<ExpertQ2SourceSegment> segments;
};
void configure_expert_q2_source_segments(std::vector<ExpertQ2SourceSegments>);
}
