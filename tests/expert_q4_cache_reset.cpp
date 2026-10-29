// SPDX-License-Identifier: MIT
#include "expert_q4_cache_reset.h"
#include <array>
#include <cassert>
#include <iostream>
#include <vector>
struct Policy{void reset(unsigned,unsigned,unsigned,unsigned){}};
struct LRU{
    int n_expert=512,n_slots=481,n_protected=10,head[2]={5,9},tail[2]={7,11};
    bool adaptive=false;Policy policy;unsigned seen_gen=7;
    std::vector<int>key_of,prev,next,seen,uniq;std::vector<bool>is_protected;
    std::array<std::array<int,512>,48>maps;std::vector<int*>slot_map;
    explicit LRU(unsigned slots=481):n_slots(slots),key_of(slots,-1),prev(slots),next(slots),seen(512),is_protected(slots),slot_map(49,nullptr){
        for(unsigned i=0;i<48;++i){maps[i].fill(-1);slot_map[i]=maps[i].data();}
    }
};
int main(){
    LRU empty;assert(qwen_app::reset_expert_q4_cache_metadata(empty,48)==0);
    LRU filled;for(int slot=0;slot<481;++slot){const int key=slot*17;filled.key_of[slot]=key;filled.slot_map[key/512][key%512]=slot;}
    const auto maps=filled.slot_map;assert(qwen_app::reset_expert_q4_cache_metadata(filled,48)==481&&filled.slot_map==maps);
    assert(filled.head[0]==0&&filled.tail[0]==480&&filled.head[1]==-1&&filled.tail[1]==-1&&filled.seen_gen==0);
    for(int slot=0;slot<481;++slot)assert(filled.key_of[slot]==-1&&filled.prev[slot]==slot-1&&filled.next[slot]==(slot==480?-1:slot+1));
    unsigned refused=0;auto reject=[&](LRU&lru){try{qwen_app::reset_expert_q4_cache_metadata(lru,48);return false;}catch(const std::exception&){++refused;return true;}};
    LRU wrong(480);assert(reject(wrong));
    LRU missing;missing.slot_map[47]=nullptr;assert(reject(missing));
    LRU corrupt;corrupt.slot_map[0][0]=480;assert(reject(corrupt));
    LRU inverse;inverse.key_of[480]=24575;assert(reject(inverse));
    LRU seen;seen.seen.pop_back();assert(reject(seen));
    try{qwen_app::reset_resident_cache_metadata(empty,48);return 3;}catch(const std::exception&){++refused;}
    LRU original53(53),original128(128);assert(qwen_app::reset_resident_cache_metadata(original53,48)==0&&qwen_app::reset_resident_cache_metadata(original128,48)==0);
    std::cout<<"{\"Q4_cache_metadata_reset_passed\":true,\"invalid_or_cross_format_resets_refused\":"<<refused<<",\"GPU_operations\":0}\n";
}
