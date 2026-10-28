// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cstdint>
#include <stdexcept>
struct qwen_resident_cache_reset_stats {
    std::uint64_t groups,maps,slots,occupied_before,occupied_after,reset_ordinal;
    bool original_banks_retained,cumulative_counters_preserved,predictive;
};
extern "C" void qwen_app_configure_resident_cache_reuse(bool);
extern "C" void qwen_app_reset_resident_expert_cache(qwen_resident_cache_reset_stats *);
extern "C" unsigned qwen_app_resident_cache_reuse_live_owners();
namespace qwen_app {
// Reset only CPU lookup/LRU/LFU metadata. Existing bank allocations and every
// slot-map pointer remain owned by the same original model/context.
template<class LRU> std::uint64_t reset_resident_cache_metadata(LRU &lru,unsigned cached_layers){
    if(lru.n_expert!=512||(lru.n_slots!=53&&lru.n_slots!=128)||lru.slot_map.size()!=49||cached_layers!=48||
       lru.key_of.size()!=std::size_t(lru.n_slots)||lru.prev.size()!=lru.key_of.size()||
       lru.next.size()!=lru.key_of.size()||lru.is_protected.size()!=lru.key_of.size()||lru.seen.size()!=512)
        throw std::runtime_error("Original retained cache metadata geometry required");
    std::uint64_t occupied=0;unsigned mapped=0;
    for(unsigned layer=0;layer<49;++layer){const auto *map=lru.slot_map[layer];if(!map)continue;++mapped;
        for(unsigned expert=0;expert<512;++expert){const auto slot=map[expert];
            if(slot<-1||slot>=lru.n_slots||(slot>=0&&lru.key_of[slot]!=int(layer*512+expert)))
                throw std::runtime_error("Existing Expert lookup is inconsistent before reset");}}
    if(mapped!=cached_layers)throw std::runtime_error("Every original trunk lookup must remain bound");
    for(unsigned slot=0;slot<lru.key_of.size();++slot){const auto key=lru.key_of[slot];if(key<0){if(key!=-1)throw std::runtime_error("Invalid empty cache key");continue;}
        if(key>=49*512||!lru.slot_map[key/512]||lru.slot_map[key/512][key%512]!=int(slot)){
            throw std::runtime_error("Existing cache slot is inconsistent before reset");}
        ++occupied;}
    if(lru.adaptive)lru.policy.reset(49,512,lru.n_slots,cached_layers);
    for(auto *map:lru.slot_map)if(map)std::fill_n(map,512,-1);
    std::fill(lru.key_of.begin(),lru.key_of.end(),-1);
    for(int slot=0;slot<lru.n_slots;++slot){lru.prev[slot]=slot-1;lru.next[slot]=slot+1<lru.n_slots?slot+1:-1;}
    lru.head[0]=0;lru.tail[0]=lru.n_slots-1;lru.head[1]=lru.tail[1]=-1;lru.n_protected=0;
    std::fill(lru.is_protected.begin(),lru.is_protected.end(),false);
    std::fill(lru.seen.begin(),lru.seen.end(),0);lru.seen_gen=0;lru.uniq.clear();return occupied;
}
}
