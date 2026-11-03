// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
// Observe the selected engine's cumulative compact counters. This grants no
// allocation credit and never changes snapshot ownership or reserve checks.
inline void require_compact_mtp_request(const std::uint64_t*before,const std::uint64_t*after,
    unsigned attempts,unsigned rejected){
    if(!before||!after||!attempts||attempts>6||rejected>attempts||after[0]<before[0]||after[1]<before[1]||
       after[0]-before[0]!=attempts||after[1]-before[1]!=rejected)
        throw std::runtime_error("Every target attempt and rejection needs its actual completed compact counter");
}
}
