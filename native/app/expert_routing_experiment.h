// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
// Ranking changes only; downstream mixture weights use the original probabilities.
inline void cache_rank_scores(const float*source,float*target,const unsigned char*resident,
        std::size_t count,float bonus){
    if(!source||!target||!resident||count!=512||!std::isfinite(bonus)||bonus<1||bonus>2)
        throw std::invalid_argument("Bounded cache-aware ranking required");
    for(std::size_t i=0;i<count;++i){
        if(!std::isfinite(source[i])||source[i]<0)throw std::runtime_error("Finite nonnegative routing probabilities required");
        target[i]=source[i]*(resident[i]?bonus:1.0f);
    }
}
inline unsigned experimental_expert_count(unsigned mode,unsigned width){
    if(mode>4||width<1||width>4)throw std::invalid_argument("Unknown bounded routing mode or width");
    return width==1&&mode==2?8:width==1&&mode==3?6:10;
}
}
struct ggml_tensor;
extern "C" unsigned qwen_app_route_mode();
extern "C" bool qwen_app_route_is_decode();
extern "C" void qwen_app_route_phase(bool);
extern "C" void qwen_app_route_begin(unsigned);
extern "C" void qwen_app_route_resident(unsigned,unsigned,bool);
extern "C" void qwen_app_route_stats(std::uint64_t*);
extern "C" void qwen_app_route_rank(ggml_tensor*,const ggml_tensor*,int,int,void*);
