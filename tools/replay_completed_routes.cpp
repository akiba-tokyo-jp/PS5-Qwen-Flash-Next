// SPDX-License-Identifier: MIT
// Read-only fixed-route capacity screen using the actual selected policy.
#include "expert_temporal_probation.h"
#include <iostream>
#include <set>
int main(){try{
    unsigned slots,requests;if(!(std::cin>>slots>>requests))return 2;
    qwen_app::TemporalProbationPolicy policy;std::vector<std::int32_t>keys;
    std::vector<std::int32_t>resident(49*512,-1);
    for(unsigned request=0;request<requests;++request){unsigned reset,records;std::cin>>reset>>records;
        if(reset){policy.reset(49,512,slots,48);keys.assign(slots,-1);std::fill(resident.begin(),resident.end(),-1);}
        std::uint64_t hits=0,misses=0;
        for(unsigned record=0;record<records;++record){unsigned layer,n;std::cin>>layer>>n;
            std::vector<std::int32_t>ids;std::set<std::int32_t>seen;
            for(unsigned i=0;i<n;++i){std::int32_t id;std::cin>>id;if(seen.insert(id).second)ids.push_back(id);}
            policy.observe(layer,ids);for(auto id:ids)if(resident.at(layer*512+id)>=0)++hits;
            std::sort(ids.begin(),ids.end());
            for(auto id:ids){const auto key=layer*512+id;if(resident.at(key)>=0)continue;
                const auto slot=policy.victim(keys,layer,ids);if(slot<0)throw std::runtime_error("No eligible slot");
                if(keys.at(slot)>=0)resident.at(keys[slot])=-1;
                keys[slot]=key;resident.at(key)=slot;++misses;
                std::cerr<<request<<' '<<layer<<' '<<id<<'\n';
            }
        }std::cout<<request<<' '<<hits<<' '<<misses<<'\n';
    }return std::cin?0:2;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
