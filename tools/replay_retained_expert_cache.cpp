// SPDX-License-Identifier: MIT
// Host-only replay: route-residency notifications are already reflected in the
// captured ordered IDs. This does not simulate new cache-aware model outputs.
#include "expert_policy.h"
#include "indexed_probation_policy.h"
#include "resident_weight_retention.h"
#include <array>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#define GGML_ASSERT(v) do { if (!(v)) throw std::runtime_error("Frozen planner assertion: " #v); } while (0)
#define GGML_ABORT(...) throw std::runtime_error("Frozen planner aborted")
extern "C" bool llama_app_expert_policy_enabled() { return true; }
extern "C" void qwen_app_route_resident(unsigned, unsigned, bool) {}
#include "current-cache.private.h"
using Json = nlohmann::json;

int main(int argc, char **argv) try {
    if (argc != 3) throw std::runtime_error("Input and output paths required");
    std::ifstream input(argv[1]); Json traces; input >> traces;
    Json output = Json::array();
    moe_cache_slru planner; planner.init(49, 512, 3072, 48);
    std::array<std::array<int, 512>, 48> maps{};
    for (unsigned layer = 0; layer < 48; ++layer) {
        maps[layer].fill(-1); planner.slot_map[layer] = maps[layer].data();
    }
    for (const auto &trace : traces) {
        std::uint64_t hits = 0, misses = 0, unique = 0;
        Json records = Json::array(), states = Json::array();
        auto initial = planner.key_of;
        for (const auto &row : trace.at("records")) {
            const auto layer = row.at("layer").get<unsigned>();
            const auto tokens = row.at("tokens").get<unsigned>();
            const auto experts = row.at("experts").get<unsigned>();
            auto ids = row.at("ids").get<std::vector<int>>();
            if (layer >= 48 || !tokens || tokens > 32 || !experts || experts > 10 || ids.size() != tokens * experts)
                throw std::runtime_error("Unbounded route row");
            auto before = planner.key_of;
            std::vector<moe_cache_slru::fill> fills; std::size_t hit = 0;
            if (!planner.plan(layer, ids.data(), ids.size(), fills, hit))
                throw std::runtime_error("Frozen planner refused");
            hits += hit; misses += fills.size(); unique += hit + fills.size();
            Json entries = Json::array();
            for (const auto &item : fills)
                entries.push_back({{"expert", item.expert}, {"slot", item.slot}, {"previous_key", before.at(item.slot)}});
            if (layer == 47) states.push_back(planner.key_of);
            records.push_back({{"layer", layer}, {"tokens", tokens}, {"experts", experts}, {"misses", entries}, {"hits", hit}});
        }
        if (hits != trace.at("cache_hits") || misses != trace.at("cache_misses") ||
            unique != trace.at("unique_selected_experts") || misses * 1536000ULL != trace.at("uploaded_bytes"))
            throw std::runtime_error("Native and replay cache counters differ");
        const auto occupied = qwen_app::validate_retained_weight_cache(planner, 48, 3072);
        output.push_back({{"ordinal", trace.at("ordinal")}, {"hits", hits}, {"misses", misses}, {"unique", unique},
            {"records", records}, {"initial_residents", initial}, {"after_process_residents", states}, {"occupied_slots", occupied}});
    }
    std::ofstream out(argv[2]); out << output.dump() << '\n';
    if (!out) throw std::runtime_error("Host replay output failed");
    std::cout << "PASS: all three native3072-slot retained-cache sequences and bidirectional ownership\n";
    return 0;
} catch (const std::exception &error) { std::cerr << error.what() << '\n'; return 1; }
