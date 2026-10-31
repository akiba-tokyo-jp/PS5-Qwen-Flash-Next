// SPDX-License-Identifier: MIT
#include "expert_policy.h"
#include "indexed_probation_policy.h"
#include "resident_weight_retention.h"
#include <array>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#define GGML_ASSERT(v) do {if(!(v))throw std::runtime_error("Frozen planner assertion");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Frozen planner aborted")
extern "C" bool llama_app_expert_policy_enabled(){return true;}
extern "C" void qwen_app_route_resident(unsigned,unsigned,bool){}
inline const std::vector<bool>*screen_protected=nullptr;
#include "screen-cache.private.h"
using Json=nlohmann::json;
int main(int argc,char**argv)try{
    if(argc!=4)throw std::runtime_error("Traces, phase bounds and output required");
    Json traces,bounds;std::ifstream(argv[1])>>traces;std::ifstream(argv[2])>>bounds;Json results=Json::array();
    for(unsigned cap:{0,512,1024,1536}){
        moe_cache_slru p;p.init(49,512,3072,48);std::array<std::array<int,512>,48>maps{};
        for(unsigned l=0;l<48;++l){maps[l].fill(-1);p.slot_map[l]=maps[l].data();}
        std::vector<int>previous;Json requests=Json::array();
        for(unsigned i=0;i<traces.size();++i){const auto&t=traces[i];std::vector<bool>protect(49*512,false);
            for(unsigned n=0;n<std::min<std::size_t>(cap,previous.size());++n)protect[previous[previous.size()-1-n]]=true;
            std::vector<int>decode;std::array<std::uint64_t,3>misses{};std::uint64_t hits=0;
            const unsigned pre=bounds[i]["before_first_token_processes"],last=bounds[i]["through_last_token_processes"];
            unsigned index=0;
            for(const auto&r:t["records"]){const unsigned layer=r["layer"],process=index++/48;const unsigned phase=process<pre?0:process<last?1:2;
                auto ids=r["ids"].get<std::vector<int>>();screen_protected=phase==0&&cap?&protect:nullptr;
                std::vector<moe_cache_slru::fill>fills;std::size_t hit=0;
                if(!p.plan(layer,ids.data(),ids.size(),fills,hit))throw std::runtime_error("Planner refused");
                misses[phase]+=fills.size();hits+=hit;
                if(phase==1)for(int id:ids){int key=int(layer)*512+id;auto it=std::find(decode.begin(),decode.end(),key);
                    if(it!=decode.end())decode.erase(it);decode.push_back(key);}
            }
            const auto total=misses[0]+misses[1]+misses[2];
            if(!cap&&(total!=t["cache_misses"]||hits!=t["cache_hits"]))throw std::runtime_error("Control differs from native");
            qwen_app::validate_retained_weight_cache(p,48,3072);
            requests.push_back({{"ordinal",i},{"prefill_misses",misses[0]},{"decode_misses",misses[1]},{"EOS_misses",misses[2]},{"total_misses",total}});previous=decode;
        }
        results.push_back({{"protection_cap",cap},{"requests",requests}});
    }
    // Exercise the real indexed policy aging boundary with all keys protected:
    // fallback must preserve exactly the original eligible victim.
    qwen_app::IndexedProbationPolicy a,b;a.reset(2,4,4,2);b.reset(2,4,4,2);std::vector<int>keys{0,1,4,5};
    for(int s=0;s<4;++s){a.replaced(s,-1,keys[s]);b.replaced(s,-1,keys[s]);}
    std::vector<bool>all(8,true);for(int n=0;n<4200;++n){a.observe(n%2,{n%4});b.observe(n%2,{n%4});}
    if(a.victim(keys,0,{0})!=b.victim_avoiding(keys,0,{0},&all))throw std::runtime_error("Aging/fallback differs");
    std::ofstream out(argv[3]);out<<Json({{"control_exact",true},{"aging_and_all_protected_fallback_passed",true},{"results",results}}).dump(2)<<'\n';
    std::cout<<"PASS: native control, bounded protection screens, ownership, aging and fallback\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
