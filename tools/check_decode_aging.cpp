// SPDX-License-Identifier: MIT
#include "expert_policy.h"
#include "indexed_probation_policy.h"
#include "resident_weight_retention.h"
#include <array>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#define GGML_ASSERT(v) do{if(!(v))throw std::runtime_error("Frozen cache assertion");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Frozen cache abort")
extern "C" bool llama_app_expert_policy_enabled(){return true;}
extern "C" void qwen_app_route_resident(unsigned,unsigned,bool){}
#include "current-cache.private.h"
int main(int argc,char**argv)try{
    if(argc!=2)throw std::runtime_error("Four-input captured routes required");nlohmann::json traces;std::ifstream(argv[1])>>traces;
    moe_cache_slru p;p.init(49,512,3072,48);std::array<std::array<int,512>,48>maps{};
    for(unsigned l=0;l<48;++l){maps[l].fill(-1);p.slot_map[l]=maps[l].data();}
    unsigned observations=0;
    for(unsigned request=0;request<20;++request){const auto&t=traces.at(request%4);std::uint64_t hits=0,misses=0;
        for(const auto&r:t.at("records")){auto ids=r.at("ids").get<std::vector<int>>();std::size_t hit=0;std::vector<moe_cache_slru::fill>fills;
            if(!p.plan(r.at("layer").get<int>(),ids.data(),ids.size(),fills,hit))throw std::runtime_error("Retained planner refused");
            ++observations;hits+=hit;misses+=fills.size();qwen_app::validate_retained_weight_cache(p,48,3072);}
        if(request<4&&(hits!=t.at("cache_hits")||misses!=t.at("cache_misses")))throw std::runtime_error("Initial four native controls differ");
    }
    if(observations<8192)throw std::runtime_error("Two actual aging boundaries required");
    std::cout<<"PASS:49/512/3072 geometry, first four native counters exact,20 different-input trace requests retained across "<<observations<<" observations, two4096-observation boundaries and bidirectional ownership after every route\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
