/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bitmap glyphs adapted from PS5-Vulkan-Inference src/demo_renderer.cpp.
 * Copyright (C) 2026 BlackBearReloaded
 * Copyright (C) 2026 Mihawk-99
 * Application monitor layout and drawing integration: PS5 Qwen contributors.
 */
#include "monitor.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <ctime>

namespace qwen_app {
namespace {
constexpr std::uint32_t background = 0xff111813, panel = 0xff1c2820, accent = 0xff9ddbcb, ink = 0xffe3eee4, muted = 0xffa0b6a4;
struct Glyph { char character; std::array<unsigned char, 7> rows; };
constexpr Glyph glyphs[] = {
    {' ',{0,0,0,0,0,0,0}}, {'0',{14,17,19,21,25,17,14}}, {'1',{4,12,4,4,4,4,14}},
    {'2',{14,17,1,2,4,8,31}}, {'3',{30,1,1,14,1,1,30}}, {'4',{2,6,10,18,31,2,2}},
    {'5',{31,16,16,30,1,1,30}}, {'6',{14,16,16,30,17,17,14}}, {'7',{31,1,2,4,8,8,8}},
    {'8',{14,17,17,14,17,17,14}}, {'9',{14,17,17,15,1,1,14}}, {'A',{14,17,17,31,17,17,17}},
    {'B',{30,17,17,30,17,17,30}}, {'C',{14,17,16,16,16,17,14}}, {'D',{30,17,17,17,17,17,30}},
    {'E',{31,16,16,30,16,16,31}}, {'F',{31,16,16,30,16,16,16}}, {'G',{14,17,16,23,17,17,14}},
    {'H',{17,17,17,31,17,17,17}}, {'I',{31,4,4,4,4,4,31}}, {'J',{7,2,2,2,18,18,12}},
    {'K',{17,18,20,24,20,18,17}}, {'L',{16,16,16,16,16,16,31}}, {'M',{17,27,21,21,17,17,17}},
    {'N',{17,25,21,19,17,17,17}}, {'O',{14,17,17,17,17,17,14}}, {'P',{30,17,17,30,16,16,16}},
    {'Q',{14,17,17,17,21,18,13}}, {'R',{30,17,17,30,20,18,17}}, {'S',{15,16,16,14,1,1,30}},
    {'T',{31,4,4,4,4,4,4}}, {'U',{17,17,17,17,17,17,14}}, {'V',{17,17,17,17,17,10,4}},
    {'W',{17,17,17,21,21,21,10}}, {'X',{17,17,10,4,10,17,17}}, {'Y',{17,17,10,4,4,4,4}},
    {'Z',{31,1,2,4,8,16,31}}, {'.',{0,0,0,0,0,6,6}}, {':',{0,6,6,0,6,6,0}},
    {'-',{0,0,0,31,0,0,0}}, {'/',{1,2,2,4,8,8,16}}, {'%',{25,25,2,4,8,19,19}},
    {'?',{14,17,1,2,4,0,4}}, {'+',{0,4,4,31,4,4,0}}, {'(',{2,4,8,8,8,4,2}}, {')',{8,4,2,2,2,4,8}}
};
std::string decimal(std::optional<double> value, const char * unit = "", double divisor = 1) {
    if (!value || !std::isfinite(*value)) return "--";
    char buffer[64]; std::snprintf(buffer, sizeof(buffer), "%.2f%s", *value / divisor, unit); return buffer;
}
std::string memory(std::optional<std::uint64_t> value) {
    return value ? decimal(double(*value), " GIB", double(std::uint64_t(1) << 30)) : "--";
}
}
MonitorRaster::MonitorRaster() : pixels_(width * height) {}
void MonitorRaster::rect(int x, int y, int w, int h, std::uint32_t color) {
    const int left = std::max(0, x), top = std::max(0, y), right = std::min(int(width), x + w), bottom = std::min(int(height), y + h);
    for (int row = top; row < bottom; ++row)
        if (right > left) std::fill(pixels_.begin() + row * width + left, pixels_.begin() + row * width + right, color);
}
void MonitorRaster::text(int x, int y, const std::string & value, int scale, std::uint32_t color) {
    for (unsigned char c : value) {
        if (c >= 'a' && c <= 'z') c -= 'a' - 'A';
        const Glyph * glyph = &glyphs[0];
        for (const auto & candidate : glyphs) if (candidate.character == c) { glyph = &candidate; break; }
        for (int row = 0; row < 7; ++row) for (int column = 0; column < 5; ++column)
            if (glyph->rows[row] & (1 << (4 - column))) rect(x + column * scale, y + row * scale, scale, scale, color);
        x += 6 * scale;
        if (x + 5 * scale >= int(width) - 48) break;
    }
}
void MonitorRaster::line(int x0, int y0, int x1, int y1, std::uint32_t color) {
    const int dx = std::abs(x1 - x0), sx = x0 < x1 ? 1 : -1, dy = -std::abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int error = dx + dy;
    for (;;) {
        rect(x0, y0, 2, 2, color);
        if (x0 == x1 && y0 == y1) break;
        const int twice = 2 * error;
        if (twice >= dy) { error += dy; x0 += sx; }
        if (twice <= dx) { error += dx; y0 += sy; }
    }
}
void MonitorRaster::draw(const MonitorSnapshot & s) {
    std::fill(pixels_.begin(), pixels_.end(), background);
    if (s.request_id != request_) { request_ = s.request_id; samples_ = 0; rates_.fill(0); }
    std::move(rates_.begin() + 1, rates_.end(), rates_.begin());
    rates_.back() = s.tokens_per_second && std::isfinite(*s.tokens_per_second) ? std::clamp(*s.tokens_per_second, 0.0, 1000000.0) : 0;
    samples_ = std::min(samples_ + 1, rates_.size());
    text(60, 48, "PS5 QWEN / FLASH NEXT", 4, accent);
    text(60, 100, "ORIGINAL BF16 / INFERENCE MONITOR", 3, muted);
    if (s.epoch_ms) {
        const std::time_t stamp = std::time_t(s.epoch_ms / 1000);
        std::tm utc{};
#if defined(_WIN32)
        const bool valid = gmtime_s(&utc, &stamp) == 0;
#else
        const bool valid = gmtime_r(&stamp, &utc) != nullptr;
#endif
        if (valid) {
            char date[64]; std::strftime(date, sizeof(date),
                s.clock_calibrated ? "%Y-%m-%d %H:%M:%S UTC SYNC" : "%Y-%m-%d %H:%M:%S DEVICE TIME", &utc);
            text(1250, 65, date, 3, ink);
        }
    }
    rect(48, 165, 1824, 54, panel);
    text(68, 181, s.quarantined ? "BACKEND QUARANTINED / RESOURCES RETAINED" : "STATE: " + s.state, 3, s.quarantined ? 0xff9b9bff : ink);
    rect(48, 245, 1000, 350, panel); rect(1072, 245, 800, 350, panel);
    text(72, 270, s.busy ? "GENERATION / LAST 5 SECONDS" : "LAST SESSION / DECODE AVERAGE", 3, muted);
    text(72, 323, decimal(s.tokens_per_second), 11, accent); text(650, 365, "TOKENS/S", 4, ink);
    text(72, 430, "INCLUDES REASONING AND ANSWER TOKENS", 3, muted);
    const double maximum = std::max(1.0, *std::max_element(rates_.begin(), rates_.end()));
    for (std::size_t i = 1; i < samples_; ++i) {
        const auto a = rates_.size() - samples_ + i - 1, b = a + 1;
        line(75 + int(i - 1) * 15, 568 - int(rates_[a] / maximum * 75), 75 + int(i) * 15, 568 - int(rates_[b] / maximum * 75), accent);
    }
    text(1100, 278, "GENERATED TOKENS", 3, muted); text(1100, 318, std::to_string(s.generated_tokens), 6, ink);
    text(1100, 404, "TIME TO FIRST TOKEN", 3, muted); text(1570, 404, decimal(s.ttft_ms, " S", 1000), 3, ink);
    text(1100, 464, "ELAPSED", 3, muted); text(1570, 464, decimal(s.elapsed_ms, " S", 1000), 3, ink);
    text(1100, 535, s.model_loaded ? "MODEL LOADED" : "MODEL NOT LOADED", 3, accent);
    rect(48, 619, 890, 213, panel); rect(962, 619, 910, 213, panel);
    text(72, 643, "CPU", 3, accent); text(72, 684, s.cpu_name.empty() ? "IDENTITY UNAVAILABLE" : s.cpu_name.substr(0, 45), 3, ink);
    text(72, 744, "APP CPU USE: " + decimal(s.cpu_percent, "%"), 3, muted);
    text(72, 790, "LOGICAL THREADS: " + (s.cpu_threads ? std::to_string(s.cpu_threads) : "--"), 3, muted);
    text(986, 643, "GPU", 3, accent); text(986, 684, s.gpu_name.empty() ? "IDENTITY UNAVAILABLE" : s.gpu_name.substr(0, 45), 3, ink);
    text(986, 744, "GPU USE: " + decimal(s.gpu_percent, "%"), 3, muted);
    text(986, 790, "MEMORY: " + memory(s.gpu_total_bytes) + " / " + memory(s.gpu_free_bytes), 3, muted);
    rect(48, 856, 1824, 112, panel);
    std::string hit = "--", uploaded = "--";
    if (s.expert_cache) {
        const auto & c = *s.expert_cache;
        if (c.hits || c.misses) hit = decimal(100.0 * double(c.hits) / (double(c.hits) + double(c.misses)), "%");
        uploaded = memory(c.uploaded_bytes);
    }
    text(72, 878, "EXPERT CACHE HIT: " + hit + " / UPLOAD: " + uploaded, 3, ink);
    text(72, 927, "SHARED MEMORY / NO EXTRA VRAM / UNKNOWN COUNTERS STAY --", 3, muted);
    text(60, 1005, s.message.empty() ? "READ-ONLY DISPLAY / INFERENCE IS CONTROLLED EXTERNALLY" : s.message.substr(0, 96), 3, accent);
}
} // namespace qwen_app
