// SPDX-License-Identifier: MIT
#pragma once
#include "expert_routing_experiment.h"
namespace qwen_app {
struct RoutingPolicy { unsigned experts;bool cache_rank,sharing; };
// Bits 0-1 select 10/8/6; bit 2 adds cache ranking; bit 3 adds causal sharing.
inline RoutingPolicy routing_policy(unsigned bits){
    if(bits>14||(bits&3)==3)throw std::invalid_argument("Unknown bounded routing policy");
    return {unsigned((bits&3)==1?8:(bits&3)==2?6:10),bool(bits&4),bool(bits&8)};
}
inline unsigned decode_policy_experts(unsigned bits,unsigned width){
    if(width<1||width>4)throw std::invalid_argument("Unknown bounded policy graph width");
    const auto p=routing_policy(bits);return width<=2?p.experts:10;
}
}
extern "C" void qwen_app_routing_event_begin();
