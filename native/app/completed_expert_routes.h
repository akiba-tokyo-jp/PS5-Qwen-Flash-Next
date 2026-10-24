// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace qwen_app {
inline constexpr std::uint32_t expert_route_layers=48;
inline constexpr std::uint32_t expert_route_capacity=4608;
struct CompletedExpertRoute {
    std::uint8_t layer=0, tokens=0;
    std::array<std::uint16_t,40> ids{};
};
class ExpertRouteCaptureError:public std::runtime_error {
public:using std::runtime_error::runtime_error;
};
// Observe IDs the existing cache has already downloaded and synchronized.
// This never submits a download, changes routing, or chooses a cache victim.
// Metadata refusal quarantines capture and produces an explicit failed report;
// original API calls still pass through. Original API failures still propagate.
void begin_completed_expert_routes();
std::vector<CompletedExpertRoute> finish_completed_expert_routes(std::uint64_t completed_process_calls);
bool completed_expert_routes_pending();
void quarantine_completed_expert_routes();
} // namespace qwen_app
