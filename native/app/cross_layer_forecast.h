// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <stdexcept>
#include <vector>
namespace qwen_app {
// Fixed-size, past-only transition table. This is the native implementation of
// the screened two-anchor heuristic, not a neural router or a route oracle.
class CrossLayerForecast {
    struct Target {int id=-1;unsigned count=0;};
    struct Entry {
        int layer=-1,a=-1,b=-1;unsigned seen=0;
        std::uint64_t at=0;std::array<Target,16> targets{};
    };
    std::vector<Entry> table_=std::vector<Entry>(512);
    std::array<int,10> previous_{};
    int previous_layer_=-1;std::uint64_t tick_=0;
    Entry *find(int layer,int a,int b) {
        for(auto &e:table_)if(e.layer==layer&&e.a==a&&e.b==b)return &e;
        return nullptr;
    }
public:
    void observe(unsigned layer,unsigned tokens,const int *ids,std::size_t count) {
        if(layer>=48||tokens<1||tokens>4||!ids||count!=tokens*10)
            throw std::invalid_argument("Complete original route dimensions are required for forecasting");
        for(std::size_t i=0;i<count;++i)if(ids[i]<0||ids[i]>=512)
            throw std::invalid_argument("Forecast route IDs exceed the original Expert vocabulary");
        if(tokens!=1){previous_layer_=-1;return;}
        for(unsigned i=0;i<10;++i)for(unsigned j=0;j<i;++j)if(ids[i]==ids[j])
            throw std::invalid_argument("A token route must select ten distinct original Experts");
        if(previous_layer_+1==int(layer)&&previous_layer_>=0) {
            ++tick_;auto *entry=find(int(layer),previous_[0],previous_[1]);
            if(!entry) {
                entry=&*std::min_element(table_.begin(),table_.end(),[](const Entry &a,const Entry &b){
                    return a.at<b.at;});
                *entry=Entry{};entry->layer=int(layer);entry->a=previous_[0];entry->b=previous_[1];
            }
            auto &e=*entry;
            if(e.seen>=1024){e.seen/=2;for(auto &t:e.targets){t.count/=2;if(!t.count)t.id=-1;}}
            ++e.seen;e.at=tick_;
            // Rank all prior sixteen and current ten before truncating. Do not
            // evict a frequent target merely because an early new ID arrives.
            std::array<Target,26> candidates{};std::copy(e.targets.begin(),e.targets.end(),candidates.begin());
            for(unsigned i=0;i<10;++i) {
                auto it=std::find_if(candidates.begin(),candidates.end(),[&](const Target &t){return t.id==ids[i];});
                if(it==candidates.end())it=std::find_if(candidates.begin(),candidates.end(),[](const Target &t){return t.id<0;});
                if(it==candidates.end())throw std::logic_error("Bounded forecast storage is inconsistent");
                it->id=ids[i];++it->count;
            }
            std::sort(candidates.begin(),candidates.end(),[](const Target &a,const Target &b){
                return a.count!=b.count?a.count>b.count:a.id<b.id;});
            std::copy_n(candidates.begin(),16,e.targets.begin());
        }
        std::copy_n(ids,10,previous_.begin());previous_layer_=int(layer);
    }
    int predict(unsigned target_layer,const std::vector<int> &resident_keys) {
        if(target_layer>=48||previous_layer_+1!=int(target_layer)||previous_layer_<0)return -1;
        auto *e=find(int(target_layer),previous_[0],previous_[1]);
        if(!e||e->seen<2)return -1;
        for(const auto &t:e->targets)if(t.id>=0&&t.count*4>=e->seen*3&&
            std::find(resident_keys.begin(),resident_keys.end(),int(target_layer)*512+t.id)==resident_keys.end())return t.id;
        return -1;
    }
};
}
