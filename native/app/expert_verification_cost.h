// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cmath>
#include <cstddef>
#include <stdexcept>

namespace qwen_app {
// Metadata only. Route acquisition, probabilities and complete native rollback
// require separate qualification before this selector can control a model.
struct ExpertVerificationCost {
    unsigned width=1;
    double expected_committed=1, predicted_seconds=0;
    bool past_routes_available=false;
};
inline unsigned choose_expert_verification_width(
        const std::array<ExpertVerificationCost,3>& candidates) {
    double best=0;
    unsigned selected=1;
    for(std::size_t i=0;i<candidates.size();++i) {
        const auto &c=candidates[i];
        const unsigned expected_width=i==0?1:(i==1?2:4);
        if(c.width!=expected_width||!std::isfinite(c.expected_committed)||
           !std::isfinite(c.predicted_seconds)||c.expected_committed<1||
           c.expected_committed>c.width||c.predicted_seconds<=0)
            throw std::invalid_argument("Bounded finite expert verification costs are required");
        if(!i&&!c.past_routes_available)
            throw std::invalid_argument("The ordinary control cost must be available");
        if(!c.past_routes_available)continue;
        const auto rate=c.expected_committed/c.predicted_seconds;
        // Exact ties retain the smaller width. More accepted tokens alone do
        // not justify a larger expert union or a more expensive checkpoint.
        if(rate>best){best=rate;selected=c.width;}
    }
    return selected;
}
}
