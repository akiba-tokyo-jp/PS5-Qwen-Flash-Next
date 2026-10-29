// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
// The physical Q8-output candidate keeps 998 planes. Only empty CPU metadata
// changes between 867/997 active slots; no GPU bank is allocated or released.
template<class LRU>std::uint64_t reset_resident_output_Q8_cache(LRU&lru,unsigned layers,unsigned selected){
    if((selected!=867&&selected!=997)||(lru.n_slots!=867&&lru.n_slots!=997)||lru.n_expert!=512||
       layers!=48||lru.slot_map.size()!=49||lru.key_of.size()!=std::size_t(lru.n_slots)||
       lru.prev.size()!=lru.key_of.size()||lru.next.size()!=lru.key_of.size()||
       lru.is_protected.size()!=lru.key_of.size()||lru.seen.size()!=512)
        throw std::runtime_error("Resident output Q8 quota escaped its two exact metadata geometries");
    std::uint64_t occupied=0;unsigned maps=0;
    for(unsigned layer=0;layer<49;++layer){const auto*map=lru.slot_map[layer];if(!map)continue;++maps;
        for(unsigned expert=0;expert<512;++expert){const auto slot=map[expert];
            if(slot<-1||slot>=lru.n_slots||(slot>=0&&lru.key_of[slot]!=int(layer*512+expert)))
                throw std::runtime_error("Output Q8 cache lookup is inconsistent before reset");}}
    if(maps!=48)throw std::runtime_error("Every original trunk lookup must remain bound");
    for(int slot=0;slot<lru.n_slots;++slot){const auto key=lru.key_of[slot];if(key<0){
        if(key!=-1)throw std::runtime_error("Invalid empty output Q8 cache key");continue;}
        if(key>=49*512||!lru.slot_map[key/512]||lru.slot_map[key/512][key%512]!=slot)
            throw std::runtime_error("Output Q8 cache slot is inconsistent before reset");++occupied;
    }
    for(auto*map:lru.slot_map)if(map)std::fill_n(map,512,-1);
    const auto bindings=lru.slot_map;
    lru.init(49,512,int(selected),48);
    if(lru.slot_map.size()!=bindings.size()||lru.n_slots!=int(selected))
        throw std::runtime_error("Empty Q8 metadata reinitialization changed its shape");
    std::copy(bindings.begin(),bindings.end(),lru.slot_map.begin());
    for(auto*map:lru.slot_map)if(map)for(unsigned e=0;e<512;++e)if(map[e]!=-1)
        throw std::runtime_error("A Q8 quota switch retained an occupied lookup");
    return occupied;
}
}
