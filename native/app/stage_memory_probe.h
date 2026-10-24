// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
namespace qwen_app {
inline constexpr std::size_t stage_memory_probe_capacity=2048;
inline constexpr std::uint64_t stage_memory_probe_idle_ns=2000000;
struct StageMemorySample {
    char phase[96];
    std::uint64_t idle_before_ns=0,before_ns=0,write_after_ns=0,after_ns=0;
    std::uint32_t free_idle_before=0,free_before=0,free_after_write=0,free_after=0;
    bool valid=false;
};
// Explicit CPU-only diagnostic; normal bootstrap and inference keep it disabled.
bool begin_native_stage_memory_probe();
bool end_native_stage_memory_probe();
std::size_t native_stage_memory_probe_count();
const StageMemorySample * native_stage_memory_probe_sample(std::size_t);
}
