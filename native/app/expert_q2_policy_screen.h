// SPDX-License-Identifier: MIT
#pragma once
#include "expert_policy.h"

namespace qwen_app {
// Offline candidates only. Runtime selection is deliberately absent until a
// same-model console comparison qualifies a particular policy.
enum class Q2PolicyMode { control, recency, short_age, phase_history, probation, flexible_floor };
inline Q2PolicyMode q2_screen_mode = Q2PolicyMode::control;
inline unsigned q2_screen_tokens = 1;

class Q2ScreenPolicy {
    ExpertPolicy control_;
    std::size_t experts_=0,slots_=0,cached_layers_=0,routes_=0;
    std::uint64_t tick_=0;
    std::vector<std::uint32_t> counts_,decode_,prefill_;
    std::vector<std::uint64_t> recency_;
    std::vector<std::size_t> residents_;
    static void increment(std::uint32_t &v) {if(v!=UINT32_MAX)++v;}
public:
    void reset(std::size_t layers,std::size_t experts,std::size_t slots,std::size_t cached_layers) {
        control_.reset(layers,experts,slots,cached_layers);
        experts_=experts;slots_=slots;cached_layers_=cached_layers;routes_=0;tick_=0;
        counts_.assign(layers*experts,0);decode_=counts_;prefill_=counts_;
        recency_.assign(counts_.size(),0);residents_.assign(layers,0);
    }
    void observe(std::int32_t layer,const std::vector<std::int32_t>&ids) {
        control_.observe(layer,ids);++tick_;
        for(auto id:ids) {
            const auto key=std::size_t(layer)*experts_+id;
            increment(counts_.at(key));recency_.at(key)=tick_;
            increment((q2_screen_tokens==1?decode_:prefill_).at(key));
        }
        const auto interval=q2_screen_mode==Q2PolicyMode::short_age?192u:4096u;
        if(++routes_==interval) {
            for(auto *values:{&counts_,&decode_,&prefill_})for(auto &v:*values)v/=2;
            routes_=0;
        }
    }
    std::int32_t victim(const std::vector<std::int32_t>&keys,std::int32_t active,
                        const std::vector<std::int32_t>&selected) {
        if(q2_screen_mode==Q2PolicyMode::control)return control_.victim(keys,active,selected);
        if(keys.size()!=slots_||selected.size()>slots_)return -1;
        std::fill(residents_.begin(),residents_.end(),0);
        for(auto key:keys)if(key>=0)++residents_.at(std::size_t(key)/experts_);
        const auto floor=q2_screen_mode==Q2PolicyMode::flexible_floor?0:(slots_-selected.size())/cached_layers_;
        auto score=[&](std::size_t key)->std::uint64_t {
            switch(q2_screen_mode) {
            case Q2PolicyMode::recency:return 0;
            case Q2PolicyMode::phase_history:return std::uint64_t(decode_[key])*4+prefill_[key];
            case Q2PolicyMode::probation:return counts_[key]>=2?1:0;
            default:return counts_[key];
            }
        };
        std::int32_t best=-1;
        for(std::size_t slot=0;slot<keys.size();++slot) {
            const auto key=keys[slot];if(key<0)return std::int32_t(slot);
            const auto layer=std::size_t(key)/experts_;
            if(layer==std::size_t(active)) {
                if(std::find(selected.begin(),selected.end(),std::int32_t(key%experts_))!=selected.end())continue;
            }else if(residents_[layer]<=floor)continue;
            if(best<0||score(key)<score(keys[best])||
               (score(key)==score(keys[best])&&recency_[key]<recency_[keys[best]]))best=std::int32_t(slot);
        }
        return best;
    }
};
}
