// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
namespace qwen_app {
inline bool original_predictive_model_geometry(std::uint32_t trunk,std::uint32_t total,
        std::uint32_t mtp,std::uint32_t experts,std::uint32_t selected) {
    // The original model retains the separate MTP block. Forecast only the
    // 48 trunk layers; retaining that block does not add a forecast layer.
    return trunk==48&&total==49&&mtp==1&&experts==512&&selected==10;
}
}
