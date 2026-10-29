// SPDX-License-Identifier: MIT
#pragma once
#include <resident_cache_reset.h>
namespace qwen_app {
// Same complete metadata invariants as the original reset, with one explicit
// Q2-only capacity. GPU banks, counters and source data are never modified.
template<class LRU>std::uint64_t reset_expert_q2_cache_metadata(LRU&lru,unsigned cached_layers){
    if(lru.n_expert!=512||lru.n_slots!=581||lru.slot_map.size()!=49||cached_layers!=48||
       lru.key_of.size()!=581||lru.prev.size()!=lru.key_of.size()||lru.next.size()!=lru.key_of.size()||
       lru.is_protected.size()!=lru.key_of.size()||lru.seen.size()!=512)
        throw std::runtime_error("Exact 581-slot Q2 retained cache metadata geometry required");
    std::uint64_t occupied=0;unsigned mapped=0;
    for(unsigned layer=0;layer<49;++layer){const auto*map=lru.slot_map[layer];if(!map)continue;++mapped;
        for(unsigned expert=0;expert<512;++expert){const auto slot=map[expert];
            if(slot<-1||slot>=581||(slot>=0&&lru.key_of[slot]!=int(layer*512+expert)))
                throw std::runtime_error("Existing Q2 Expert lookup is inconsistent before reset");}}
    if(mapped!=48)throw std::runtime_error("All 48 original trunk lookups must remain bound");
    for(unsigned slot=0;slot<581;++slot){const auto key=lru.key_of[slot];if(key<0){
            if(key!=-1)throw std::runtime_error("Invalid empty Q2 cache key");continue;}
        if(key>=49*512||!lru.slot_map[key/512]||lru.slot_map[key/512][key%512]!=int(slot))
            throw std::runtime_error("Existing Q2 cache slot is inconsistent before reset");
        ++occupied;}
    if(lru.adaptive)lru.policy.reset(49,512,581,48);
    for(auto*map:lru.slot_map)if(map)std::fill_n(map,512,-1);
    std::fill(lru.key_of.begin(),lru.key_of.end(),-1);
    for(int slot=0;slot<581;++slot){lru.prev[slot]=slot-1;lru.next[slot]=slot+1<581?slot+1:-1;}
    lru.head[0]=0;lru.tail[0]=580;lru.head[1]=lru.tail[1]=-1;lru.n_protected=0;
    std::fill(lru.is_protected.begin(),lru.is_protected.end(),false);
    std::fill(lru.seen.begin(),lru.seen.end(),0);lru.seen_gen=0;lru.uniq.clear();return occupied;
}
}
