// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// Application pread occupancy, not a hardware SSD queue-depth measurement.
// One producer and its existing worker remain the only admitted callers.
class SourceIOOccupancy {
    std::atomic_flag lock_=ATOMIC_FLAG_INIT;
    std::uint64_t last_=0,active_=0,maximum_=0,calls_=0,overlapping_starts_=0;
    std::array<std::uint64_t,3> times_{};
    static std::uint64_t now() noexcept {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
    }
    void acquire() noexcept {while(lock_.test_and_set(std::memory_order_acquire)) {}}
    void release() noexcept {lock_.clear(std::memory_order_release);}
    void advance() noexcept {
        const auto t=now();if(last_)times_[active_]+=t-last_;last_=t;
    }
public:
    void begin() {
        acquire();advance();
        if(active_>=2){release();throw std::runtime_error("Source occupancy exceeded its two owned lanes");}
        ++calls_;if(active_)++overlapping_starts_;++active_;if(active_>maximum_)maximum_=active_;release();
    }
    void end() noexcept {acquire();advance();if(active_)--active_;release();}
    std::array<std::uint64_t,7> snapshot() {
        acquire();advance();const std::array<std::uint64_t,7> out{
            calls_,overlapping_starts_,times_[0],times_[1],times_[2],maximum_,active_};release();return out;
    }
};
}
extern "C" void qwen_app_source_io_occupancy(std::uint64_t*,std::size_t);
