// SPDX-License-Identifier: MIT
#pragma once
#include <atomic>
#include <cstdint>
namespace qwen_throughput {
inline std::atomic<unsigned> mode{0};
inline std::uint64_t stats[12]{};
}
