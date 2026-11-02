// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// The caller serializes the authoritative update and its shadow under one lock.
// A latched event remains immutable across both verification rows and rollback.
class GpuCacheRankSnapshot {
    std::array<unsigned char,49*512> live_{},event_{};
    bool latched_=false;
public:
    void reset(){live_.fill(0);event_.fill(0);latched_=false;}
    void resident(unsigned layer,unsigned expert,bool present){
        if(layer>=49||expert>=512)throw std::invalid_argument("GPU rank residency exceeds the current model");
        live_[layer*512+expert]=present;
    }
    void latch(){event_=live_;latched_=true;}
    void coefficients(unsigned layer,float*out,std::size_t count)const{
        if(!latched_||layer>=48||!out||count!=512)throw std::invalid_argument("One latched complete GPU rank layer is required");
        for(unsigned i=0;i<512;++i)out[i]=event_[layer*512+i]?1.5f:1.0f;
    }
    void coefficients_all(float*out,std::size_t count)const{
        if(!latched_||!out||count!=48*512)throw std::invalid_argument("One complete latched trunk ranking matrix is required");
        for(unsigned i=0;i<48*512;++i)out[i]=event_[i]?1.5f:1.0f;
    }
};
}
