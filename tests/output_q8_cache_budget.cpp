// SPDX-License-Identifier: MIT
#include "resident_output_q8_cache_reset.h"
#include "resident_output_q8_profile.h"
#include <device_buffer_budget.h>
#include <array>
#include <iostream>
#include <vector>
struct LRU {
    int n_slots=997,n_expert=512;
    std::vector<int*>slot_map;
    std::vector<int>key_of,prev,next;
    std::vector<bool>is_protected;
    std::vector<unsigned>seen;
    void init(unsigned layers,unsigned experts,int slots,unsigned){
        n_slots=slots;n_expert=int(experts);slot_map.assign(layers,nullptr);
        key_of.assign(slots,-1);prev.resize(slots);next.resize(slots);
        is_protected.assign(slots,false);seen.assign(experts,0);
    }
};
void require(bool value){if(!value)throw std::runtime_error("Output Q8 budget/control failed");}
template<class F>void rejects(F f){bool refused=false;try{f();}catch(const std::exception&){refused=true;}require(refused);}
int main(){try{
    using namespace qwen_app;
    std::array<std::array<int,512>,48>maps{};for(auto&map:maps)map.fill(-1);
    LRU lru;lru.init(49,512,997,48);for(unsigned i=0;i<48;++i)lru.slot_map[i]=maps[i].data();
    const auto bindings=lru.slot_map;lru.key_of[996]=511;maps[0][511]=996;
    require(reset_resident_output_Q8_cache(lru,48,867)==1&&lru.n_slots==867&&lru.slot_map==bindings);
    require(maps[0][511]==-1);lru.key_of[866]=512+7;maps[1][7]=866;
    require(reset_resident_output_Q8_cache(lru,48,997)==1&&lru.n_slots==997&&maps[1][7]==-1);
    rejects([&]{reset_resident_output_Q8_cache(lru,48,998);});
    lru.key_of[996]=0;rejects([&]{reset_resident_output_Q8_cache(lru,48,867);});lru.key_of[996]=-1;
    lru.slot_map[47]=nullptr;rejects([&]{reset_resident_output_Q8_cache(lru,48,867);});lru.slot_map=bindings;
    require(resident_output_Q8_cache_transfer==199680000&&resident_output_Q8_payload_saving==595968000);
    const auto rounded=[](std::uint64_t n){return(n+(2ull<<20)-1)&~((2ull<<20)-1);};
    const std::array<std::uint64_t,3>roles{537600,537600,460800};std::uint64_t old=0,now=0;
    for(auto size:roles){old+=rounded(868*size);now+=rounded(998*size);require(rounded(998*size)<=model_postload_single_buffer);}
    require(now-old<=resident_output_Q8_cache_transfer);
    require(resident_output_Q8_postload_budget==model_postload_device_budget);
    require(resident_output_Q8_cache_transfer+(16ull<<20)<resident_output_Q8_payload_saving);
    DeviceBufferBudget ledger;ledger.enable();std::array<int,5>keys{};
    for(unsigned i=0;i<3;++i){ledger.reserve(998*roles[i]);ledger.commit(&keys[i]);}
    ledger.workspace(&keys[3],{1,1,1,1});ledger.reserve(120ull<<20);ledger.commit(&keys[4]);
    require(ledger.stats().live<=model_postload_device_budget);
    for(auto&key:keys)ledger.released(&key);ledger.close_completed();
    DeviceBufferBudget bad;bad.enable();rejects([&]{bad.reserve(model_postload_single_buffer+1);});
    std::cout<<"Q8 867/997 reset, retained mappings, invalid slots/owners and actual rounded bank limits passed\n";
}catch(const std::exception&e){std::cerr<<e.what();return 1;}}
