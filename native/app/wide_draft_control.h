// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <thread>
#include <vector>

namespace qwen_app {
// Experimental single-producer sidecar. No production engine layout changes.
struct WideDraftPlan {
    unsigned width=2;
    std::array<std::int32_t,3> drafts{};
};
class WideDraftControl {
    std::thread::id producer_=std::this_thread::get_id();
    const void *engine_=nullptr;
    WideDraftPlan plan_{};
    bool armed_=false;
    unsigned decisions_=0,last_prefix_=0;
public:
    void arm(const void *engine,const std::array<std::int32_t,3>&drafts) {
        if(std::this_thread::get_id()!=producer_||!engine||armed_)
            throw std::invalid_argument("One inactive wide-draft owner is required");
        for(auto token:drafts)if(token<0||token>=248320)
            throw std::invalid_argument("Wide drafts require original vocabulary IDs");
        engine_=engine;plan_={4,drafts};armed_=true;
    }
    WideDraftPlan consume(const void *engine,std::int32_t first) {
        if(std::this_thread::get_id()!=producer_)
            throw std::invalid_argument("Wide drafts are producer-thread bound");
        if(!armed_)return {2,{first,0,0}};
        if(engine!=engine_||first!=plan_.drafts[0])
            throw std::invalid_argument("Wide draft owner or first token changed");
        armed_=false;return plan_;
    }
    void decision(unsigned prefix) {
        if(std::this_thread::get_id()!=producer_||armed_||prefix>3)
            throw std::invalid_argument("A completed wide verification is required");
        ++decisions_;last_prefix_=prefix;engine_=nullptr;
    }
    unsigned decisions()const{return decisions_;}
    unsigned last_prefix()const{return last_prefix_;}
};
extern WideDraftControl wide_draft_control;

inline void pop_verified_logits(std::vector<float>&queued,std::vector<float>&current,
                               std::size_t columns,bool&more) {
    if(!columns||columns>262144||queued.empty()||queued.size()%columns||queued.size()/columns>3)
        throw std::invalid_argument("Verified logits require one to three complete rows");
    for(float value:queued)if(!std::isfinite(value))
        throw std::invalid_argument("Verified logits must remain finite");
    if(queued.size()==columns){current=std::move(queued);queued.clear();more=false;}
    else {current.assign(queued.begin(),queued.begin()+columns);queued.erase(queued.begin(),queued.begin()+columns);more=true;}
}
}
