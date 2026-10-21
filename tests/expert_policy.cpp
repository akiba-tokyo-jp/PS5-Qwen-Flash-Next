// SPDX-License-Identifier: MIT
// The tested slot planner is extracted from the patched pinned engine source.
#include "expert_policy.h"
#include <cstring>
#include <iostream>
#include <string>

static bool adaptive = true;
extern "C" bool llama_app_expert_policy_enabled() { return adaptive; }
#define GGML_ASSERT(value) do { if (!(value)) throw std::runtime_error("Engine assertion: " #value); } while (0)
#define GGML_ABORT(...) throw std::runtime_error("Engine cache has no victim")
#include "engine-plan-under-test.h"

static void check(bool value, const char * message) { if (!value) throw std::runtime_error(message); }

static void replay(bool use_policy) {
    adaptive = use_policy;
    constexpr int layers = 4, experts = 16, capacity = 10, width = 7;
    moe_cache_slru planner;
    planner.init(layers, experts, capacity, layers);
    std::vector<std::vector<std::int32_t>> mapping(layers, std::vector<std::int32_t>(experts, -1));
    for (int layer = 0; layer < layers; ++layer) planner.slot_map[layer] = mapping[layer].data();
    std::vector<std::uint16_t> original(layers * experts * width), bank(capacity * width);
    // Include signed zeros, subnormals, finite extrema and NaN payload bit patterns.
    for (std::size_t i = 0; i < original.size(); ++i) original[i] = std::uint16_t(i * 129 + 0x8000);
    const auto unchanged = original;
    std::size_t total_hits = 0, total_misses = 0;
    for (int route = 0; route < 8200; ++route) {
        const int layer = route % layers;
        const int first = route % 7 ? layer : route % experts;
        const std::int32_t selected[] = {first, (first + 1) % experts, first, (first + 3) % experts};
        std::vector<moe_cache_slru::fill> fills; std::size_t hits = 0;
        check(planner.plan(layer, selected, 4, fills, hits), "Valid expert route rejected");
        check(hits + fills.size() == 3, "Duplicate route IDs counted as separate cache requests");
        for (const auto & fill : fills)
            std::memcpy(bank.data() + fill.slot * width, original.data() + (layer * experts + fill.expert) * width,
                        width * sizeof(std::uint16_t));
        for (auto expert : selected) {
            const auto slot = mapping[layer][expert];
            check(slot >= 0 && slot < capacity, "An active expert was evicted");
            check(!std::memcmp(bank.data() + slot * width, original.data() + (layer * experts + expert) * width,
                               width * sizeof(std::uint16_t)), "BF16 source bits changed or stale cache slot used");
        }
        for (int l = 0; l < layers; ++l) for (int e = 0; e < experts; ++e) {
            const auto slot = mapping[l][e];
            check(slot < 0 || planner.key_of[slot] == l * experts + e, "Evicted expert retained a stale slot map");
        }
        total_hits += hits; total_misses += fills.size();
    }
    check(original == unchanged && total_hits && total_misses, "Replay did not exercise exact cache hits and misses");
    std::int32_t too_many[11]; for (int i = 0; i < 11; ++i) too_many[i] = i;
    const auto keys = planner.key_of;
    std::vector<moe_cache_slru::fill> fills; std::size_t hits = 0;
    check(!planner.plan(0, too_many, 11, fills, hits) && planner.key_of == keys,
          "Oversized active set partially changed residency");
}

int main() {
    try {
        using namespace qwen_app;
        check(uma_cache_budget(100, 80, 120, 50) == 70, "UMA free pools were added or reserve ignored");
        check(uma_cache_budget(100, 0, 120, 50) == 0 && uma_cache_budget(100, 100, 49, 50) == 0,
              "Unknown or exhausted memory was admitted");
        check(uma_cache_budget(UINT64_MAX, UINT64_MAX, UINT64_MAX, UINT64_MAX) == 0,
              "UMA reserve subtraction underflowed");
        ExpertPolicy policy; policy.reset(2, 8, 4, 2);
        for (int i = 0; i < 4096; ++i) policy.observe(0, {1});
        check(policy.count(1) == 2048, "Maya frequency counts did not age at 4096 routes");
        policy.reset(2, 8, 4, 2);
        policy.observe(0, {1}); policy.observe(0, {2}); policy.observe(1, {1, 2});
        check(policy.victim({1, 2, 9, 10}, 0, {2}) == 0, "Equal-frequency eviction did not use recency");
        check(policy.victim({1, 2, 3, 9}, 0, {2}) != 3, "A layer lost its feasible residency floor");
        check(policy.victim({1, 2, 3, 9}, 0, {1, 2, 3}) == 3, "Floor blocked a complete active set");
        policy.reset(1, 8, 3, 1);
        for (int i = 0; i < 10; ++i) policy.observe(0, {1});
        policy.observe(0, {2}); policy.observe(0, {3});
        check(policy.victim({1, 2, 3}, 0, {3}) == 1, "Frequency policy evicted an older hot expert");
        auto range = expert_advice_range(4097, 4096, 4096, 8192);
        check(range.address == 4096 && range.bytes == 8192, "Page advice rounding is wrong");
        check(!expert_advice_range(4097, 4096, 4096, 8191).bytes &&
              !expert_advice_range(UINTPTR_MAX - 1, 4, 4096, SIZE_MAX).bytes,
              "Advice exceeded its budget or overflowed an address");
        replay(true); replay(false);
        std::cout << "Expert policy: UMA admission, aging, recency, layer floors, active-set pinning, advice bounds, "
                     "and 16,400 actual planner routes with bit-exact BF16 fixtures passed\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
