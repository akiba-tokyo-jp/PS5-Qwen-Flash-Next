// SPDX-License-Identifier: MIT
#pragma once
#include <chrono>
#include <cstdint>
#include <optional>
#include <stdexcept>

namespace qwen_app {
struct ClockCalibration {
    std::int64_t console_epoch_ms = 0, utc_epoch_ms = 0, uncertainty_ms = 0;
};

// Configuration is immutable before HTTP/display threads start. This changes
// only the application's clock; it never sets the console's system clock.
class MonitorClock {
public:
    using Steady = std::chrono::steady_clock;
    static std::int64_t system_epoch_ms() {
        return std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
    }
    void initialize(const std::optional<ClockCalibration> & calibration,
                    std::int64_t console_now = system_epoch_ms(),
                    Steady::time_point steady_now = Steady::now()) {
        if (initialized_) throw std::logic_error("Monitor clock is already initialized");
        std::int64_t anchor = console_now;
        if (calibration) {
            const auto & c = *calibration;
            constexpr std::int64_t earliest = 946684800000LL, latest = 4102444800000LL;
            if (c.console_epoch_ms < earliest || c.console_epoch_ms > latest ||
                c.utc_epoch_ms < earliest || c.utc_epoch_ms > latest ||
                console_now < earliest || console_now > latest ||
                c.uncertainty_ms < 0 || c.uncertainty_ms > 5000)
                throw std::invalid_argument("Monitor clock calibration is outside its bounds");
            const auto age = console_now - c.console_epoch_ms;
            const auto offset = c.utc_epoch_ms - c.console_epoch_ms;
            if (age < -c.uncertainty_ms || age > 15 * 60 * 1000 ||
                offset < -86400000 || offset > 86400000)
                throw std::invalid_argument("Monitor clock calibration is stale or inconsistent");
            anchor = console_now + offset;
            calibrated_ = true;
            uncertainty_ = c.uncertainty_ms;
        }
        epoch_ = anchor; steady_ = steady_now; initialized_ = true;
    }
    std::int64_t now(Steady::time_point steady_now = Steady::now()) const {
        if (!initialized_) return system_epoch_ms();
        return epoch_ + std::chrono::duration_cast<std::chrono::milliseconds>(steady_now - steady_).count();
    }
    bool calibrated() const { return calibrated_; }
    std::optional<std::int64_t> initial_uncertainty_ms() const { return uncertainty_; }
    const char * source() const { return calibrated_ ? "host-calibrated UTC" : "device time (unverified)"; }
private:
    bool initialized_ = false, calibrated_ = false;
    std::int64_t epoch_ = 0;
    Steady::time_point steady_{};
    std::optional<std::int64_t> uncertainty_;
};
inline MonitorClock & monitor_clock() { static MonitorClock clock; return clock; }
}
