// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include <array>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace qwen_app {
struct MonitorSnapshot {
    std::string state = "starting", request_id, cpu_name, gpu_name, message;
    unsigned cpu_threads = 0;
    bool model_loaded = false, busy = false, quarantined = false, clock_calibrated = false;
    std::uint64_t epoch_ms = 0, generated_tokens = 0;
    std::optional<double> tokens_per_second, ttft_ms, elapsed_ms, cpu_percent, gpu_percent;
    std::optional<std::uint64_t> gpu_total_bytes, gpu_free_bytes;
    std::optional<ExpertCacheMetrics> expert_cache;
};

// A bounded CPU renderer shared by the native VideoOut surface and host image
// checks. It has no input, chat, controller or generation operations.
class MonitorRaster {
public:
    static constexpr unsigned width = 1920, height = 1080;
    MonitorRaster();
    void draw(const MonitorSnapshot & snapshot);
    const std::vector<std::uint32_t> & pixels() const { return pixels_; }
private:
    void rect(int x, int y, int w, int h, std::uint32_t color);
    void text(int x, int y, const std::string & value, int scale, std::uint32_t color);
    void line(int x0, int y0, int x1, int y1, std::uint32_t color);
    std::vector<std::uint32_t> pixels_;
    std::array<double, 60> rates_{};
    std::size_t samples_ = 0;
    std::string request_;
};
} // namespace qwen_app
