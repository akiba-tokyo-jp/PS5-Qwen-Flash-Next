// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
namespace qwen_app {
inline constexpr std::uint64_t resident_output_Q8_payload_saving=595968000;
inline constexpr std::uint64_t resident_output_Q8_cache_transfer=199680000;
inline constexpr std::uint64_t resident_output_Q8_cache_budget=1533419520;
inline constexpr std::uint64_t resident_output_Q8_postload_budget=(1792ull<<20)+resident_output_Q8_cache_transfer;
static_assert(resident_output_Q8_cache_transfer<resident_output_Q8_payload_saving-(16ull<<20),
    "The quota transfer must retain more than the old resident requirement's rounding allowance");
}
