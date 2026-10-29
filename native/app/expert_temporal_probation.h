// SPDX-License-Identifier: MIT
#pragma once
#ifndef QWEN_TEMPORAL_BASE_PROVIDED
#include "expert_policy.h"
#endif

namespace qwen_app {
// A bounded age for two-touch protection; zero preserves qualified probation.
// Runtime selectors may change only before an empty-context policy reset.
inline unsigned temporal_probation_window=0;
class TemporalProbationPolicy {
    std::size_t experts_=0,slots_=0,cached_layers_=0,routes_=0;
    std::uint64_t tick_=0;
    std::vector<std::uint32_t> counts_;
    std::vector<std::uint64_t> recency_;
    std::vector<std::size_t> residents_;
public:
    void set_eviction_policy(ExpertEvictionPolicy policy){
        if(policy!=ExpertEvictionPolicy::two_touch_probation||tick_||routes_)
            throw std::invalid_argument("Temporal protection requires an empty probation history");
    }
    void reset(std::size_t layers,std::size_t experts,std::size_t slots,std::size_t cached_layers){
        if(!layers||!experts||!slots||!cached_layers||cached_layers>layers||layers>std::size_t(INT32_MAX)/experts)
            throw std::invalid_argument("Invalid temporal cache geometry");
        experts_=experts;slots_=slots;cached_layers_=cached_layers;routes_=0;tick_=0;
        counts_.assign(layers*experts,0);recency_.assign(layers*experts,0);residents_.resize(layers);
    }
    void observe(std::int32_t layer,const std::vector<std::int32_t>&ids){
        ++tick_;for(auto id:ids){const auto key=std::size_t(layer)*experts_+id;
            if(counts_.at(key)!=UINT32_MAX)++counts_[key];recency_.at(key)=tick_;}
        if(++routes_==4096){for(auto&count:counts_)count/=2;routes_=0;}
    }
    std::int32_t victim(const std::vector<std::int32_t>&keys,std::int32_t active,const std::vector<std::int32_t>&selected){
        if(keys.size()!=slots_||selected.size()>slots_)return -1;
        std::fill(residents_.begin(),residents_.end(),0);
        for(auto key:keys)if(key>=0){if(std::size_t(key)>=counts_.size())throw std::out_of_range("Invalid temporal resident");++residents_[key/experts_];}
        const auto floor=(slots_-selected.size())/cached_layers_;
        auto score=[&](std::size_t key){return counts_[key]>=2&&(!temporal_probation_window||tick_-recency_[key]<=temporal_probation_window);};
        std::int32_t best=-1;
        for(std::size_t slot=0;slot<keys.size();++slot){const auto key=keys[slot];if(key<0)return std::int32_t(slot);
            const auto layer=std::size_t(key)/experts_;
            if(layer==std::size_t(active)){if(std::find(selected.begin(),selected.end(),std::int32_t(key%experts_))!=selected.end())continue;}
            else if(residents_[layer]<=floor)continue;
            if(best<0||score(key)<score(keys[best])||(score(key)==score(keys[best])&&recency_[key]<recency_[keys[best]]))best=std::int32_t(slot);
        }return best;
    }
    std::uint32_t count(std::size_t key)const{return counts_.at(key);}
};
}
