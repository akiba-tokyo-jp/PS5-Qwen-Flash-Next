// SPDX-License-Identifier: MIT
#include "expert_policy.h"
#include "indexed_probation_policy.h"
#include "resident_weight_retention.h"
#include "adaptive_prefill_protection.h"
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>
#define GGML_ASSERT(v) do{if(!(v))throw std::runtime_error("Actual planner assertion");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Actual planner aborted")
extern "C" bool llama_app_expert_policy_enabled(){return true;}
extern "C" void qwen_app_route_resident(unsigned,unsigned,bool){}
inline const std::vector<bool>*screen_protected=nullptr;
#include "screen-cache.private.h"
using Json=nlohmann::json;
int main(int argc,char**argv)try{
 if(argc!=3)throw std::runtime_error("Input/output required");Json input;std::ifstream(argv[1])>>input;Json result=Json::array();
 for(const auto&cohort:input)for(unsigned mode=0;mode<7;++mode){
  moe_cache_slru p;p.init(49,512,3072,48);std::array<std::array<int,512>,48>maps{};
  for(unsigned l=0;l<48;++l){maps[l].fill(-1);p.slot_map[l]=maps[l].data();}
  qwen_app::AdaptivePrefillProtection h;Json rows=Json::array();std::uint64_t total=0;
  for(const auto&t:cohort["requests"]){
   const bool clear=t.at("clear");if(clear){p.init(49,512,3072,48);for(unsigned l=0;l<48;++l){maps[l].fill(-1);p.slot_map[l]=maps[l].data();}}
   h.begin(mode!=0,clear);h.bind_prompt(t.at("prompt").get<std::vector<int>>());
   std::uint64_t misses=0,hits=0;Json fills_out=Json::array();unsigned i=0;
   const unsigned before=t.at("pre"),through=t.at("last");
   for(const auto&r:t["trace"]["records"]){unsigned process=i++/48,l=r["layer"];auto ids=r["ids"].get<std::vector<int>>();
    const bool decode=process>=before;screen_protected=h.prepare(l,ids,decode,mode==2||mode==6,mode>=3?(mode==3?8:mode==5?2:4):0);
    std::vector<moe_cache_slru::fill>fills;std::size_t hit=0;if(!p.plan(l,ids.data(),ids.size(),fills,hit))throw std::runtime_error("Planner refused");
    h.observe(l,ids,decode);misses+=fills.size();hits+=hit;
    for(const auto&f:fills)fills_out.push_back({{"layer",l},{"expert",f.expert},{"phase",process<before?0:process<through?1:2}});
    if(l==47&&process>=before&&process<through)h.commit();
   }
   qwen_app::validate_retained_weight_cache(p,48,3072);
   if(mode==cohort.at("native_mode")&&(misses!=t["trace"]["cache_misses"]||hits!=t["trace"]["cache_hits"]))throw std::runtime_error("Current native counters differ");
   rows.push_back({{"misses",misses},{"hits",hits},{"fills",fills_out}});total+=misses;
  }
  result.push_back({{"cohort",cohort["name"]},{"mode",mode},{"total_misses",total},{"requests",rows}});
 }
 std::ofstream(argv[2])<<result.dump(2)<<'\n';std::cout<<"PASS: exact selected planner, native controls, causal adaptive screens and ownership\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
