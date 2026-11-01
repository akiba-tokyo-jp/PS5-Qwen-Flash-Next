// SPDX-License-Identifier: MIT
#pragma once
#include "expert_q2_sparse.h"
#include <stdexcept>

namespace qwen_app {
// The isolated output-Q8 parent uses two whole-file parts rather than an
// Expert composite plan. Preserve its complete trailing bytes when overlaying
// the smaller output tensor; every physical source remains identity-bound.
inline std::vector<ExpertQ2SourceSegment> output_plain_segments(
        std::uint64_t logical_bytes,const std::vector<std::size_t>&parts,
        const std::vector<std::uint64_t>&physical_bytes){
    if(logical_bytes!=675430560ull||parts.size()!=2||parts[0]==parts[1]||
       parts[0]>=physical_bytes.size()||parts[1]>=physical_bytes.size()||
       physical_bytes[parts[0]]!=536870912ull||physical_bytes[parts[1]]!=138559648ull)
        throw std::runtime_error("Exact isolated output-Q8 whole-source geometry required");
    return {{0,536870912ull,parts[0],0},{536870912ull,138559648ull,parts[1],0}};
}
}
