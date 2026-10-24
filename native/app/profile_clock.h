// SPDX-License-Identifier: MIT
#pragma once
#include <chrono>
#include <cstdint>

namespace qwen_app {
using ProfileClock = std::chrono::steady_clock;
inline std::uint64_t profile_elapsed_ns(ProfileClock::time_point start) noexcept {
    const auto elapsed = std::chrono::duration_cast<std::chrono::nanoseconds>(ProfileClock::now() - start).count();
    return elapsed > 0 ? static_cast<std::uint64_t>(elapsed) : 0;
}
// Aggregate counters only: no hot-path logs, allocation or GPU operation.
class ProfileScope {
    std::uint64_t & counter_;
    ProfileClock::time_point started_ = ProfileClock::now();
public:
    explicit ProfileScope(std::uint64_t & counter) noexcept : counter_(counter) {}
    ~ProfileScope() { counter_ += profile_elapsed_ns(started_); }
    ProfileScope(const ProfileScope &) = delete;
    ProfileScope & operator=(const ProfileScope &) = delete;
};
}
