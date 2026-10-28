// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// Model-free controller. Inputs are completed whole-step costs and only the
// number of causal prompt/history proposals currently available. Diagnostic
// target-token proposals are never observations for this controller.
class AdaptiveDraftDepth {
    struct Cost {double seconds=0,committed=0;std::uint32_t samples=0;};
    std::array<Cost,3> costs_{};
    std::uint32_t decisions_=0;
public:
    void observe(unsigned width,unsigned committed,double elapsed,bool causal) {
        if((width!=1&&width!=2&&width!=4)||!committed||committed>width||
           !std::isfinite(elapsed)||elapsed<=0||!causal)
            throw std::invalid_argument("Adaptive depth requires completed causal step costs");
        const auto i=width==1?0:width==2?1:2;auto&c=costs_[i];
        if(!c.samples){c.seconds=elapsed;c.committed=committed;}
        else {c.seconds=(3*c.seconds+elapsed)/4;c.committed=(3*c.committed+committed)/4;}
        ++c.samples;
    }
    unsigned choose(unsigned causal_proposals,unsigned remaining,bool width_four_qualified) {
        if(causal_proposals>3||remaining>32)
            throw std::invalid_argument("Adaptive depth exceeds the bounded causal request");
        ++decisions_;if(!costs_[0].samples||!causal_proposals||remaining<2)return 1;
        // At most one causal calibration per previously unmeasured width.
        if(!costs_[1].samples)return 2;
        if(width_four_qualified&&causal_proposals==3&&remaining>=4&&!costs_[2].samples)return 4;
        unsigned best=1;double rate=costs_[0].committed/costs_[0].seconds;
        for(unsigned i=1;i<3;++i){const auto width=i==1?2:4;const auto&c=costs_[i];
            if(!c.samples||causal_proposals<unsigned(width-1)||remaining<unsigned(width)||(i==2&&!width_four_qualified))continue;
            const auto candidate=c.committed/c.seconds;
            if(candidate>rate){rate=candidate;best=unsigned(width);}
        }
        return best;
    }
    std::uint32_t decisions()const{return decisions_;}
};
}
