// SPDX-License-Identifier: MIT
#include "resident_weight_retention.h"
#include <array>
#include <cassert>
#include <vector>

struct Cache {
    int n_slots=3072, n_expert=512;
    std::array<std::array<int,512>,48> storage{};
    std::vector<int*> slot_map=std::vector<int*>(49,nullptr);
    std::vector<int> key_of=std::vector<int>(3072,-1);
    std::vector<int> prev=std::vector<int>(3072,-1),next=prev;
    std::vector<bool> is_protected=std::vector<bool>(3072,false);
    std::vector<unsigned> seen=std::vector<unsigned>(512,0);
    Cache(){for(unsigned l=0;l<48;++l){storage[l].fill(-1);slot_map[l]=storage[l].data();}}
};

int main(){
    Cache c;
    c.slot_map[7][13]=2000;c.key_of[2000]=7*512+13;
    const auto keys=c.key_of;const auto maps=c.storage;
    assert(qwen_app::validate_retained_weight_cache(c,48,3072)==1);
    assert(c.key_of==keys&&c.storage==maps);
    auto refuses=[&]{bool rejected=false;try{qwen_app::validate_retained_weight_cache(c,48,3072);}
                    catch(const std::runtime_error&){rejected=true;}assert(rejected);};
    c.key_of[2000]=0;refuses();c.key_of=keys;
    c.slot_map[7][13]=-1;refuses();c.storage=maps;
    c.slot_map[1]=nullptr;refuses();c.slot_map[1]=c.storage[1].data();
    c.slot_map[7][13]=3072;refuses();c.storage=maps;
    c.key_of[12]=-2;refuses();c.key_of=keys;
    c.prev.pop_back();refuses();
}
