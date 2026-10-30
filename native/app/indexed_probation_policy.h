// SPDX-License-Identifier: MIT
#pragma once
#include "expert_temporal_probation.h"
#include <set>
#include <tuple>

namespace qwen_app {
// Equivalent to TemporalProbationPolicy at window0. Each resident has one
// ordered metadata node. No weight, source lease or GPU state is retained here.
class IndexedProbationPolicy {
    using Entry=std::tuple<bool,std::uint64_t,std::int32_t>;
    std::size_t experts_=0,slots_=0,cached_layers_=0,routes_=0;
    std::uint64_t tick_=0;
    std::vector<std::uint32_t> counts_;
    std::vector<std::uint64_t> recency_;
    std::vector<std::int32_t> keys_,locations_;
    std::vector<std::set<Entry>> layers_;
    std::set<std::int32_t> empty_;
    Entry entry(std::size_t key,std::int32_t slot)const{return {counts_[key]>=2,recency_[key],slot};}
    void erase(std::size_t key,std::int32_t slot){
        if(layers_.at(key/experts_).erase(entry(key,slot))!=1)
            throw std::logic_error("Indexed resident metadata is inconsistent");
    }
public:
    void set_eviction_policy(ExpertEvictionPolicy policy){
        if(policy!=ExpertEvictionPolicy::two_touch_probation||tick_||routes_||temporal_probation_window)
            throw std::invalid_argument("Indexed policy requires fresh window0 probation");
    }
    void reset(std::size_t layers,std::size_t experts,std::size_t slots,std::size_t cached_layers){
        if(!layers||!experts||!slots||!cached_layers||cached_layers>layers||layers>std::size_t(INT32_MAX)/experts||temporal_probation_window)
            throw std::invalid_argument("Invalid indexed cache geometry");
        experts_=experts;slots_=slots;cached_layers_=cached_layers;routes_=0;tick_=0;
        counts_.assign(layers*experts,0);recency_.assign(layers*experts,0);
        keys_.assign(slots,-1);locations_.assign(layers*experts,-1);layers_.clear();layers_.resize(layers);
        empty_.clear();for(std::size_t slot=0;slot<slots;++slot)empty_.insert(std::int32_t(slot));
    }
    void observe(std::int32_t layer,const std::vector<std::int32_t>&ids){
        ++tick_;for(auto id:ids){const auto key=std::size_t(layer)*experts_+id;const auto slot=locations_.at(key);
            if(slot>=0)erase(key,slot);
            if(counts_[key]!=UINT32_MAX)++counts_[key];recency_[key]=tick_;
            if(slot>=0)layers_[key/experts_].insert(entry(key,slot));
        }
        if(++routes_==4096){
            for(auto&count:counts_)count/=2;routes_=0;
            for(auto&layer:layers_)layer.clear();
            for(std::size_t slot=0;slot<keys_.size();++slot)if(keys_[slot]>=0)
                layers_[keys_[slot]/experts_].insert(entry(keys_[slot],std::int32_t(slot)));
        }
    }
    void replaced(std::int32_t slot,std::int32_t previous,std::int32_t next){
        if(slot<0||std::size_t(slot)>=slots_||keys_[slot]!=previous||next<0||std::size_t(next)>=locations_.size()||locations_[next]>=0)
            throw std::invalid_argument("Indexed replacement is not an owned new resident");
        if(previous>=0){erase(previous,slot);locations_[previous]=-1;}else if(empty_.erase(slot)!=1)
            throw std::logic_error("Indexed empty slot is inconsistent");
        keys_[slot]=next;locations_[next]=slot;layers_[next/experts_].insert(entry(next,slot));
    }
    std::int32_t victim(const std::vector<std::int32_t>&keys,std::int32_t active,const std::vector<std::int32_t>&selected){
        if(keys.size()!=slots_||selected.size()>slots_)return -1;
        if(!empty_.empty())return *empty_.begin();
        const auto floor=(slots_-selected.size())/cached_layers_;bool have=false;Entry best{};
        for(std::size_t layer=0;layer<layers_.size();++layer){
            const auto&tree=layers_[layer];if(layer!=std::size_t(active)&&tree.size()<=floor)continue;
            auto it=tree.begin();
            if(layer==std::size_t(active))while(it!=tree.end()&&std::find(selected.begin(),selected.end(),keys_[std::get<2>(*it)]%experts_)!=selected.end())++it;
            if(it!=tree.end()&&(!have||*it<best)){best=*it;have=true;}
        }return have?std::get<2>(best):-1;
    }
    std::uint32_t count(std::size_t key)const{return counts_.at(key);}
};
}
