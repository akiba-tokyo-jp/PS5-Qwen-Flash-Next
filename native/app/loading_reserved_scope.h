// SPDX-License-Identifier: MIT
#pragma once
#include <atomic>
#include <cstdint>
#include <stdexcept>

// Include once in the native system-memory provider. The loader has completed
// CPU metadata restoration; every subsequent admission is a completed transfer
// boundary. This explicitly prices application padding, never OS counters.
static std::atomic<unsigned> qwen_loading_reserved_phase{0};
extern "C" void qwen_normal_loading_reserved_select(bool active) {
    unsigned expected=active?0u:1u;
    if(!qwen_loading_reserved_phase.compare_exchange_strong(expected,active?1u:2u))
        throw std::runtime_error("Native loading-reserve scope is once-only");
}
static std::uint64_t qwen_normal_loading_reserved_extra(
        std::uint64_t minimum,std::uint64_t reserved,std::uint64_t legacy) {
    if(qwen_loading_reserved_phase.load()!=1)return legacy;
    if(minimum!=898||reserved!=206||legacy!=256)
        throw std::runtime_error("Loading requires the exact observed OS minimum, reservation and legacy padding");
    return reserved;
}
