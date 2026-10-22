// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <thread>

namespace qwen_app {
inline constexpr std::uint64_t model_postload_device_budget = 1792ull << 20;
inline constexpr std::uint64_t model_postload_single_buffer = 512ull << 20;
struct DeviceBufferStats { std::uint64_t live = 0, peak = 0, allocations = 0; };
// This tracks GGML device buffers allocated after resident model loading. It
// excludes the already admitted model and separately reserved transfer staging.
// Round conservatively to 2 MiB, above the selected native BO granularity.
class DeviceBufferBudget {
public:
    void enable() {
        if (enabled_ || failed_) fail("The post-load device budget cannot be enabled twice");
        owner_ = std::this_thread::get_id(); enabled_ = true;
    }
    std::uint64_t reserve(std::uint64_t bytes) {
        healthy();
        if (pending_ || !bytes || bytes > model_postload_single_buffer)
            fail("The post-load device allocation exceeds its single-buffer scope");
        const auto rounded = (bytes + (2u << 20) - 1) & ~std::uint64_t((2u << 20) - 1);
        if (rounded > model_postload_device_budget - stats_.live ||
            std::none_of(entries_.begin(), entries_.end(), [](const auto & entry) { return !entry.key; }))
            fail("The aggregate post-load device allocation budget is exhausted");
        pending_ = rounded;
        return rounded;
    }
    void commit(const void * key) {
        healthy();
        if (!key || !pending_ || std::any_of(entries_.begin(), entries_.end(), [&](const auto & entry) { return entry.key == key; }))
            fail("A post-load device allocation has no unique successful reservation");
        auto entry = std::find_if(entries_.begin(), entries_.end(), [](const auto & item) { return !item.key; });
        if (entry == entries_.end()) fail("The post-load device allocation ledger is full");
        *entry = {key, pending_}; stats_.live += pending_; pending_ = 0;
        stats_.peak = std::max(stats_.peak, stats_.live); ++stats_.allocations;
    }
    void released(const void * key) {
        healthy();
        if (pending_) fail("A device allocation was freed during an incomplete reservation");
        const auto entry = std::find_if(entries_.begin(), entries_.end(), [&](const auto & item) { return item.key == key; });
        // Pre-load model buffers were admitted separately and are not charged twice.
        if (entry != entries_.end() && entry->key) { stats_.live -= entry->bytes; *entry = {}; }
    }
    DeviceBufferStats stats() { healthy(); return stats_; }
    void close_completed() {
        healthy();
        if (pending_ || stats_.live) fail("Post-load device buffers have not all completed their release");
    }
private:
    struct Entry { const void * key = nullptr; std::uint64_t bytes = 0; };
    std::array<Entry, 8192> entries_{};
    DeviceBufferStats stats_;
    std::thread::id owner_;
    std::uint64_t pending_ = 0;
    bool enabled_ = false, failed_ = false;
    [[noreturn]] void fail(const char * reason) { failed_ = true; throw std::runtime_error(reason); }
    void healthy() {
        if (!enabled_ || failed_ || owner_ != std::this_thread::get_id())
            fail("The post-load device ledger has no healthy admitted producer");
    }
};
DeviceBufferStats native_model_device_stats();
}
