// SPDX-License-Identifier: MIT
#include "expert_q2_policy_screen.h"
#include <nlohmann/json.hpp>
#include <chrono>
#include <fstream>
#include <iostream>
#define GGML_ASSERT(v) do {if(!(v))throw std::runtime_error("Planner assertion: " #v);}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Planner aborted")
extern "C" bool llama_app_expert_policy_enabled(){return true;}
#include "q2-control-plan.h"
namespace candidate {
#include "q2-candidate-plan.h"
}
namespace qwen_app {
class QualifiedProbationPolicy : public ExpertPolicy {
public:
    void reset(std::size_t layers,std::size_t experts,std::size_t slots,std::size_t cached_layers) {
        ExpertPolicy::reset(layers,experts,slots,cached_layers);
        set_eviction_policy(ExpertEvictionPolicy::two_touch_probation);
    }
};
}
namespace implementation {
#include "q2-implementation-plan.h"
}
using Json=nlohmann::json;

template<class Planner> Json replay(const Json&trace,bool record_fills=false) {
    Planner planner;planner.init(49,512,867,48);
    std::vector<std::vector<std::int32_t>> mapping(49,std::vector<std::int32_t>(512,-1));
    for(unsigned i=0;i<49;++i)planner.slot_map[i]=mapping[i].data();
    std::uint64_t hits=0,misses=0,unique=0,prefill_misses=0,decode_misses=0;
    std::array<std::uint64_t,48> layer_misses{};
    Json recorded=Json::array();
    const auto started=std::chrono::steady_clock::now();
    for(const auto&row:trace.at("records")) {
        const auto layer=row.at("layer").get<int>();
        qwen_app::q2_screen_tokens=row.at("tokens").get<unsigned>();
        const auto ids=row.at("ids").get<std::vector<std::int32_t>>();
        if(layer<0||layer>=48||ids.size()!=10*qwen_app::q2_screen_tokens||qwen_app::q2_screen_tokens>4)
            throw std::runtime_error("Unbounded route row");
        typename Planner::fill ignored{};(void)ignored;
        std::vector<typename Planner::fill> fills;std::size_t n_hit=0;
        if(!planner.plan(layer,ids.data(),ids.size(),fills,n_hit))throw std::runtime_error("Plan refused");
        hits+=n_hit;misses+=fills.size();unique+=n_hit+fills.size();layer_misses[layer]+=fills.size();
        (qwen_app::q2_screen_tokens==1?decode_misses:prefill_misses)+=fills.size();
        for(auto id:ids) {
            const auto slot=mapping[layer].at(id);
            if(slot<0||slot>=867||planner.key_of.at(slot)!=layer*512+id)throw std::runtime_error("Active Expert lost");
        }
        if(record_fills) {
            Json entries=Json::array();for(auto f:fills)entries.push_back({f.expert,f.slot});
            recorded.push_back({{"layer",layer},{"tokens",qwen_app::q2_screen_tokens},{"fills",entries}});
        }
    }
    Json result={{"hits",hits},{"misses",misses},{"unique",unique},{"Expert_uploaded_bytes",misses*1536000},
        {"prefill_misses",prefill_misses},{"width_one_misses_including_EOS",decode_misses},
        {"layer_misses",layer_misses},{"host_replay_ms",std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count()}};
    if(record_fills)result["fill_records"]=recorded;
    return result;
}
int main(int argc,char**argv) {
    try {
        if(argc!=3)throw std::runtime_error("Input and output paths required");
        std::ifstream in(argv[1]);Json inputs;in>>inputs;Json output=Json::array();
        const char*names[]={"control","recency","short_age_192","phase_history_4_to_1","two_touch_probation","flexible_layer_floor"};
        for(int mode=0;mode<6;++mode) {
            qwen_app::q2_screen_mode=static_cast<qwen_app::Q2PolicyMode>(mode);Json requests=Json::array();
            for(const auto&trace:inputs) {
                auto actual=replay<candidate::moe_cache_slru>(trace,mode==0);
                if(mode==0) {
                    auto original=replay<moe_cache_slru>(trace,true);
                    for(auto key:{"hits","misses","unique","Expert_uploaded_bytes","fill_records"})
                        if(actual[key]!=original[key])throw std::runtime_error("Original/candidate control mismatch");
                    if(actual["hits"]!=trace["cache_hits"]||actual["misses"]!=trace["cache_misses"]||
                       actual["unique"]!=trace["unique_selected_experts"]||actual["Expert_uploaded_bytes"]!=trace["uploaded_bytes"])
                        throw std::runtime_error("Native replay counters differ");
                }
                if(mode==4) {
                    auto implemented=replay<implementation::moe_cache_slru>(trace,true);
                    auto prototype=replay<candidate::moe_cache_slru>(trace,true);
                    for(auto key:{"hits","misses","unique","Expert_uploaded_bytes","fill_records"})
                        if(implemented[key]!=prototype[key])throw std::runtime_error("Implemented probation differs from screened prototype");
                }
                actual["case"]=trace.at("case");actual["ordinal"]=trace.at("ordinal");requests.push_back(actual);
            }
            output.push_back({{"mode",names[mode]},{"requests",requests}});
        }
        std::ofstream out(argv[2]);out<<output.dump()<<'\n';
        std::cout<<"Actual 867-slot planner control, full fill order, native counters, and five causal policy candidates passed\n";
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
