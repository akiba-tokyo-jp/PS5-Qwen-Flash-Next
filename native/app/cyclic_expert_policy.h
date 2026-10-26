// SPDX-License-Identifier: MIT
#pragma once
#include "expert_policy.h"
#include <array>
namespace qwen_app {
enum class CyclicEviction {control,layer_distance,frequency_over_distance};
// Offline prototype only. It retains the actual aged-frequency observation
// policy and all 53 slots; known cyclic layer order supplies no future IDs.
class CyclicExpertPolicy {
    ExpertPolicy control_;
    std::array<std::uint64_t,49*512> recency_{};
    std::uint64_t tick_=0;
    CyclicEviction mode_;
    static unsigned distance(std::int32_t layer,std::int32_t active) {
        const unsigned d=unsigned((layer-active+48)%48);return d?d:48;
    }
public:
    explicit CyclicExpertPolicy(CyclicEviction mode):mode_(mode) {
        if(mode!=CyclicEviction::control&&mode!=CyclicEviction::layer_distance&&mode!=CyclicEviction::frequency_over_distance)
            throw std::invalid_argument("Unknown cyclic metadata policy");
        control_.reset(49,512,53,48);
    }
    void observe(std::int32_t layer,const std::vector<std::int32_t> &selected) {
        if(layer<0||layer>=48||selected.size()<10||selected.size()>40||tick_==UINT64_MAX)
            throw std::invalid_argument("Original text-layer selection required");
        for(auto id:selected)if(id<0||id>=512)throw std::invalid_argument("Original expert ID required");
        ++tick_;for(auto id:selected)recency_[layer*512+id]=tick_;
        control_.observe(layer,selected);
    }
    std::int32_t victim(const std::vector<std::int32_t>&keys,std::int32_t active,const std::vector<std::int32_t>&selected) {
        if(keys.size()!=53||active<0||active>=48||selected.size()<10||selected.size()>40)return -1;
        if(mode_==CyclicEviction::control)return control_.victim(keys,active,selected);
        // The actual soft floor is zero at this fixed capacity/top-k scope.
        std::int32_t best=-1;
        for(std::size_t slot=0;slot<keys.size();++slot) {
            const auto key=keys[slot];if(key<0)return std::int32_t(slot);
            if(key>=48*512)throw std::invalid_argument("Original resident expert key required");
            const auto layer=key/512;
            if(layer==active&&std::find(selected.begin(),selected.end(),key%512)!=selected.end())continue;
            if(best<0){best=std::int32_t(slot);continue;}
            const auto old=keys[best];const auto d=distance(layer,active),previous=distance(old/512,active);
            const auto count=control_.count(key),old_count=control_.count(old);
            bool less=false,equal=false;
            if(mode_==CyclicEviction::layer_distance) {
                less=d>previous||(d==previous&&count<old_count);equal=d==previous&&count==old_count;
            }else {
                const auto a=std::uint64_t(count)*previous,b=std::uint64_t(old_count)*d;
                less=a<b;equal=a==b;
            }
            if(less||(equal&&recency_[key]<recency_[old]))best=std::int32_t(slot);
        }
        return best;
    }
};
}
