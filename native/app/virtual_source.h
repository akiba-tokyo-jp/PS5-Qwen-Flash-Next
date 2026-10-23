// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
struct VirtualSourceOps {
    virtual ~VirtualSourceOps() = default;
    virtual std::uintptr_t reserve(std::size_t) = 0;
    virtual bool protection(std::uintptr_t, std::uintptr_t &, std::uintptr_t &, std::uint32_t &) = 0;
    virtual bool release(std::uintptr_t, std::size_t) = 0;
};
inline std::size_t virtual_source_span(std::uint64_t bytes) {
    if (!bytes || bytes > (512ull << 30)) throw std::invalid_argument("Invalid original source virtual span");
    return (bytes + 16383) & ~std::uint64_t(16383);
}
inline std::uintptr_t reserve_virtual_source(std::uint64_t bytes, VirtualSourceOps & ops) {
    const auto span=virtual_source_span(bytes), at=ops.reserve(span);
    if (!at || at % 16384 || at >= (1ull << 47) || span > (1ull << 47)-at)
        throw std::runtime_error("Source virtual reservation failed; no retry or speculative release");
    std::uintptr_t first=0,last=0;std::uint32_t protection=~std::uint32_t(0);
    if (!ops.protection(at,first,last,protection) || first>at || last<at+span || protection)
        throw std::runtime_error("Source virtual protection is unknown; reservation retained for ordinary OS close");
    return at;
}
inline void release_virtual_source(std::uintptr_t at,std::uint64_t bytes,VirtualSourceOps & ops) {
    const auto span=virtual_source_span(bytes);
    if (!at || at%16384 || at>=(1ull<<47) || span>(1ull<<47)-at || !ops.release(at,span))
        throw std::runtime_error("Source virtual release did not complete; no retry");
}
std::uintptr_t reserve_native_virtual_source(std::uint64_t bytes);
void release_native_virtual_source(std::uintptr_t at,std::uint64_t bytes);
}
