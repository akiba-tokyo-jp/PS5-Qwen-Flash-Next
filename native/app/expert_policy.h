// SPDX-License-Identifier: MIT
// Portable application policy; provenance and platform adaptations: docs/expert-policy.md.
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

struct llama_app_expert_stats {
    std::uint64_t hits, misses, uploaded_bytes, prefetch_advice_bytes;
};
// Required symbols supplied by the tracked llama.cpp cache patch.
extern "C" bool llama_app_expert_policy_enabled();
extern "C" void llama_app_expert_counters(llama_app_expert_stats * result);

namespace qwen_app {

// UMA cache allocations consume the same RAM as mapped host pages. Never add
// driver free memory to OS free memory. Unknown observations must be passed as 0.
inline std::uint64_t uma_cache_budget(std::uint64_t requested, std::uint64_t driver_free,
                                      std::uint64_t os_available, std::uint64_t reserve) {
    return std::min({requested, driver_free, os_available > reserve ? os_available - reserve : 0});
}

// Maya's aged-frequency alternative, with recency breaking ties. The cache
// still copies every selected expert at its original precision. A soft layer
// floor applies only when space remains after reserving the entire active set.
class ExpertPolicy {
public:
    void reset(std::size_t layers, std::size_t experts, std::size_t slots, std::size_t cached_layers) {
        if (!layers || !experts || !slots || !cached_layers || cached_layers > layers ||
            layers > std::size_t(std::numeric_limits<std::int32_t>::max()) / experts)
            throw std::invalid_argument("Invalid expert policy dimensions");
        experts_ = experts; slots_ = slots; cached_layers_ = cached_layers;
        counts_.assign(layers * experts, 0); recency_.assign(layers * experts, 0);
        residents_.resize(layers); tick_ = 0; routes_ = 0;
    }
    void observe(std::int32_t layer, const std::vector<std::int32_t> & unique_ids) {
        ++tick_;
        for (auto expert : unique_ids) {
            const auto key = std::size_t(layer) * experts_ + expert;
            if (counts_.at(key) != std::numeric_limits<std::uint32_t>::max()) ++counts_[key];
            recency_[key] = tick_;
        }
        if (++routes_ == 4096) {
            for (auto & count : counts_) count /= 2;
            routes_ = 0;
        }
    }
    std::int32_t victim(const std::vector<std::int32_t> & keys, std::int32_t active_layer,
                        const std::vector<std::int32_t> & selected) {
        if (keys.size() != slots_ || selected.size() > slots_) return -1;
        std::fill(residents_.begin(), residents_.end(), 0);
        for (auto key : keys) {
            if (key < 0) continue;
            if (std::size_t(key) >= counts_.size()) throw std::out_of_range("Invalid resident expert key");
            ++residents_[key / experts_];
        }
        const auto floor = (slots_ - selected.size()) / cached_layers_;
        std::int32_t best = -1;
        for (std::size_t slot = 0; slot < keys.size(); ++slot) {
            const auto key = keys[slot];
            if (key < 0) return std::int32_t(slot);
            const auto layer = std::size_t(key) / experts_;
            if (layer == std::size_t(active_layer)) {
                if (std::find(selected.begin(), selected.end(), std::int32_t(key % experts_)) != selected.end()) continue;
            } else if (residents_[layer] <= floor) continue;
            if (best < 0 || counts_[key] < counts_[keys[best]] ||
                (counts_[key] == counts_[keys[best]] && recency_[key] < recency_[keys[best]]))
                best = std::int32_t(slot);
        }
        return best;
    }
    std::uint32_t count(std::size_t key) const { return counts_.at(key); }

private:
    std::size_t experts_ = 0, slots_ = 0, cached_layers_ = 0, routes_ = 0;
    std::uint64_t tick_ = 0;
    std::vector<std::uint32_t> counts_;
    std::vector<std::uint64_t> recency_;
    std::vector<std::size_t> residents_;
};

struct AdviceRange { std::uintptr_t address = 0; std::size_t bytes = 0; };
// Align advice to pages, count the rounded range against the budget, and reject
// overflow. Advice is optional: failure leaves the exact on-demand read intact.
inline AdviceRange expert_advice_range(std::uintptr_t address, std::size_t bytes,
                                       std::size_t page_size, std::size_t budget) {
    if (!bytes || !page_size || bytes > std::numeric_limits<std::uintptr_t>::max() - address) return {};
    const auto begin = address - address % page_size;
    const auto end = address + bytes;
    const auto padding = (page_size - end % page_size) % page_size;
    if (padding > std::numeric_limits<std::uintptr_t>::max() - end) return {};
    const auto rounded = end + padding - begin;
    return rounded <= budget ? AdviceRange{begin, std::size_t(rounded)} : AdviceRange{};
}
} // namespace qwen_app
