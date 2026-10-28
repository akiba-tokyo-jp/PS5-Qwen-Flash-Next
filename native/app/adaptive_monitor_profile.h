// SPDX-License-Identifier: MIT
#pragma once
#include "bounded_demo.h"
#include <cstdint>
#include <stdexcept>
#include <thread>
namespace qwen_app {
inline bool adaptive_monitor_selected=false;
inline const char*adaptive_monitor_prompt(){
    return adaptive_monitor_selected?"Copy this sequence twice exactly: red blue red blue red blue.":demo_prompt;
}
// The retained complete prefix has exactly one final consumer. Later captures
// reuse the pinned writer's storage under the independently checked budget.
class AdaptiveFinalPrefix {
    const void*engine_=nullptr,*context_=nullptr;
    std::thread::id producer_=std::this_thread::get_id();
    std::uint64_t payload_=0;
    bool certified_=false,armed_=false,consumed_=false;
public:
    void certify(const void*engine,const void*context,std::uint64_t payload,bool reset){
        if(producer_!=std::this_thread::get_id()||certified_||!engine||!context||
           payload<118038528||payload>142606336||!reset)
            throw std::runtime_error("One completed original adaptive prefix is required");
        engine_=engine;context_=context;payload_=payload;certified_=true;
    }
    void arm(const void*engine,const void*context,unsigned ordinal,bool restored){
        if(producer_!=std::this_thread::get_id()||!certified_||armed_||consumed_||engine!=engine_||context!=context_||ordinal!=2||!restored)
            throw std::runtime_error("Only the final exact restored adaptive prefix consumer is admitted");
        armed_=true;
    }
    bool pending(const void*engine,const void*context)const{
        return armed_&&!consumed_&&engine==engine_&&context==context_&&producer_==std::this_thread::get_id();
    }
    void consume(const void*engine,const void*context,std::uint64_t payload,std::int32_t position){
        if(!pending(engine,context)||payload!=payload_||position!=25)
            throw std::runtime_error("Adaptive complete prefix ownership, size or position differs");
        consumed_=true;
    }
    bool consumed()const{return consumed_;}
};
inline AdaptiveFinalPrefix adaptive_final_prefix;
}
