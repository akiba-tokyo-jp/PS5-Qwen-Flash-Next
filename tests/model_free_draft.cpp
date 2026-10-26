// SPDX-License-Identifier: MIT
#include "model_free_draft.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <functional>
#include <iostream>
#include <vector>
using namespace qwen_app;
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    const std::int32_t p[]={11,20,21,77,20,21,88},g[]={1,2,9,1,2},r[]={5,6,5,7,5},f[]={20,21};
    const auto longest=propose_model_free_token(nullptr,0,g,5,100);
    const auto recent=propose_model_free_token(nullptr,0,r,5,100);
    const auto prompt=propose_model_free_token(p,7,f,2,100);
    if(!longest.found||longest.token!=9||longest.matched_tokens!=2||longest.origin!=DraftOrigin::generated||
       !recent.found||recent.token!=7||recent.source_offset!=2||!prompt.found||prompt.token!=88||prompt.origin!=DraftOrigin::prompt||
       propose_model_free_token(p,7,nullptr,0,100).found||propose_model_free_token(p,7,f+1,1,100).found)return 3;
    std::int32_t a[]={8,3,8,99,-100},b[]={8,3,8,-20,999};
    const auto left=propose_model_free_token(p,7,a,3,100),right=propose_model_free_token(p,7,b,3,100);
    if(left.token!=3||left.token!=right.token||left.origin!=DraftOrigin::generated)return 4;
    // Every future suffix may change, including invalid values, without entering
    // the bounded history API. Candidate lookup never reads that suffix.
    for(unsigned n=1;n<=3;++n) {
        const auto x=propose_model_free_token(nullptr,0,a,n,100),y=propose_model_free_token(nullptr,0,b,n,100);
        if(x.found!=y.found||x.token!=y.token||x.matched_tokens!=y.matched_tokens)return 5;
    }
    const std::int32_t stable[]={1,2,9,1,2,9,1,2};
    const auto pair=propose_model_free_token(nullptr,0,stable,8,100,DraftEvidence::consistent_pair);
    if(!pair.found||pair.token!=9||pair.matched_tokens!=2||pair.historical_matches!=2||
       propose_model_free_token(nullptr,0,r,5,100,DraftEvidence::consistent_pair).found||
       propose_model_free_token(nullptr,0,g,5,100,DraftEvidence::consistent_pair).found)return 9;
    unsigned refused=0;
    const auto reject=[&](const std::function<void()> &run){try{run();return false;}catch(...){++refused;return true;}};
    std::vector<std::int32_t> full(256,1),bad{-1},outside{100};
    if(!reject([&]{propose_model_free_token(nullptr,1,g,5,100);})||
       !reject([&]{propose_model_free_token(p,7,nullptr,1,100);})||
       !reject([&]{propose_model_free_token(full.data(),65,g,5,100);})||
       !reject([&]{propose_model_free_token(nullptr,0,full.data(),257,100);})||
       !reject([&]{propose_model_free_token(p,7,full.data(),250,100);})||
       !reject([&]{propose_model_free_token(nullptr,0,g,5,0);})||
       !reject([&]{propose_model_free_token(nullptr,0,g,5,262145);})||
       !reject([&]{propose_model_free_token(bad.data(),1,g,5,100);})||
       !reject([&]{propose_model_free_token(outside.data(),1,g,5,100);})||
       !reject([&]{propose_model_free_token(nullptr,0,bad.data(),1,100);})||
       !reject([&]{propose_model_free_token(nullptr,0,outside.data(),1,100);})||
       !reject([&]{propose_model_free_token(nullptr,0,g,5,100,static_cast<DraftEvidence>(99));}))return 6;
    std::ifstream input(argv[1]);const auto source=nlohmann::json::parse(input);nlohmann::json rows=nlohmann::json::array();
    for(const auto &trace:source.at("requests")) {
        const auto ids=trace.at("token_ids").get<std::vector<std::int32_t>>();
        if(ids.empty()||ids.size()>32)return 7;
        nlohmann::json points=nlohmann::json::array();unsigned proposals=0,matches=0,pair_proposals=0,pair_matches=0;
        for(std::size_t n=1;n<ids.size();++n) {
            const auto draft=propose_model_free_token(nullptr,0,ids.data(),n,262144);
            const auto conservative=propose_model_free_token(nullptr,0,ids.data(),n,262144,DraftEvidence::consistent_pair);
            if(draft.found){++proposals;if(draft.token==ids[n])++matches;}
            if(conservative.found){++pair_proposals;if(conservative.token==ids[n])++pair_matches;}
            points.push_back({{"committed_generated_tokens",n},{"found",draft.found},{"draft_token",draft.token},
                {"matched_tokens",draft.matched_tokens},{"source_offset",draft.source_offset},
                {"matches_saved_next_token",draft.found&&draft.token==ids[n]},
                {"consistent_pair_found",conservative.found},{"consistent_pair_token",conservative.token},
                {"consistent_pair_matches",conservative.found&&conservative.token==ids[n]}});
        }
        rows.push_back({{"tokens",ids.size()},{"eligible_positions",ids.size()-1},{"proposals",proposals},{"matches",matches},
            {"incorrect",proposals-matches},{"consistent_pair_proposals",pair_proposals},{"consistent_pair_matches",pair_matches},
            {"consistent_pair_incorrect",pair_proposals-pair_matches},{"points",points}});
    }
    std::cout<<nlohmann::json{{"past_only_controls_passed",true},{"input_refusals",refused},{"generated_history_only",true},
        {"prompt_lookup_evaluated_on_model_trace",false},{"requests",rows},{"learned_inference",false},{"GPU_calls",0},
        {"width_two_arithmetic_or_speed_qualified",false}}.dump()<<std::endl;
}
