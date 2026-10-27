// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
// These are separate observed pools. CPU malloc uses Direct memory. Flexible
// availability is the title's library/OS quota, not global reclaimable RAM.
struct SystemMemoryObservation {
    std::uint64_t flexible_available=0;
    std::uint32_t page_size=0,kernel_pages=0,kernel_free=0;
    std::uint32_t kernel_minimum=0,kernel_target=0,kernel_reserved=0;
};
// Extra free kernel pages beyond its measured minimum; never count inactive
// pages as available. This guard does not cancel an opaque native operation.
inline constexpr std::uint64_t kernel_memory_margin=4ull<<20;
struct KernelMemoryPressure final : std::runtime_error {
    KernelMemoryPressure():std::runtime_error("Native kernel free pages do not retain their minimum and extra reserve"){}
};
inline std::uint64_t qualified_system_headroom(const SystemMemoryObservation & s) {
    if(s.page_size!=16384 || !s.flexible_available || !s.kernel_pages || !s.kernel_reserved ||
       s.kernel_reserved>s.kernel_minimum || s.kernel_minimum>=s.kernel_target ||
       s.kernel_target>s.kernel_pages || s.kernel_free>s.kernel_pages)
        throw std::runtime_error("Complete native Flexible and kernel memory observations are required");
    const auto extra=std::max<std::uint64_t>(s.kernel_reserved,kernel_memory_margin/s.page_size);
    if(s.kernel_free<std::uint64_t(s.kernel_minimum)+extra)
        throw KernelMemoryPressure();
    return s.flexible_available;
}
SystemMemoryObservation observe_native_system_memory();
struct MemoryBackpressureStats {
    std::uint64_t observations=0,pressure_events=0,recovered_admissions=0,wait_ns=0,pause_calls=0;
    bool enabled=false,last_qualified=false;
    SystemMemoryObservation last{};
};
void enable_native_memory_backpressure();
SystemMemoryObservation admit_native_system_memory();
// Stronger cold-start admission only; shares the unchanged 20 s / 60 s wait budget.
SystemMemoryObservation admit_native_startup_memory();
// Explicit model-free fixture only; shares the same 20 s / 60 s wait budget.
SystemMemoryObservation admit_native_fixture_memory(unsigned extra_operational_pages);
MemoryBackpressureStats native_memory_backpressure_stats();
// The expert buffers share Direct with the CPU heap. Flexible is a separate
// quota to preserve, not the capacity of that cache or extra allocatable RAM.
inline std::uint64_t native_direct_cache_budget(std::uint64_t requested,std::uint64_t driver_free,
                                               std::uint64_t flexible_available,std::uint64_t flexible_reserve) {
    if(!flexible_available || !flexible_reserve || flexible_available<flexible_reserve)return 0;
    return std::min(requested,driver_free);
}
}
