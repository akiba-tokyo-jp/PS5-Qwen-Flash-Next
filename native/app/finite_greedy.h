// SPDX-License-Identifier: MIT
#pragma once
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// Greedy's first-index tie rule, with the complete finite-row check retained.
// This does not construct a second vocabulary-sized candidate array.
inline std::int32_t finite_greedy(const float*values,std::size_t count) {
    if(!values||!count||count>262144)throw std::invalid_argument("Bounded complete logits required");
    std::int32_t best=0;float maximum=values[0];
    for(std::size_t i=0;i<count;++i) {
        const float value=values[i];
        if(!std::isfinite(value))throw std::runtime_error("Non-finite model logits");
        if(value>maximum) { maximum=value;best=static_cast<std::int32_t>(i); }
    }
    return best;
}
}
