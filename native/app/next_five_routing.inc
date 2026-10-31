// SPDX-License-Identifier: MIT
#include <array>
#include <algorithm>
#include <stdexcept>
namespace {
unsigned next_variant=0,next_count=6;
double next_mass=0,next_misses=0;unsigned next_rows=0;
std::uint64_t next_events[3]{},next_ranked=0;
void next_event(){
    if(next_variant==1)next_count=4;
    else if(next_variant==2)next_count=2;
    else if(next_variant==3&&next_rows){
        const auto confidence=next_mass/next_rows,misses=next_misses/next_rows;
        next_count=confidence>=0.88?2:(confidence>=0.76||misses>=3.0?4:6);
    }else next_count=6;
    ++next_events[next_count/2-1];next_mass=next_misses=0;next_rows=0;
}
void next_rank(const float*p,const unsigned char*cached){
    std::array<unsigned,512>ids{};for(unsigned i=0;i<512;++i)ids[i]=i;
    std::partial_sort(ids.begin(),ids.begin()+6,ids.end(),[&](unsigned a,unsigned b){const auto x=p[a]*(cached[a]?1.5f:1.f),y=p[b]*(cached[b]?1.5f:1.f);return x==y?a<b:x>y;});
    double all=0,four=0;unsigned misses=0;
    for(unsigned i=0;i<6;++i){all+=p[ids[i]];if(i<4)four+=p[ids[i]];misses+=!cached[ids[i]];}
    next_mass+=all?four/all:1;next_misses+=misses;++next_rows;++next_ranked;
}
}
extern "C" void qwen_next_select(unsigned v){if(v>7)throw std::invalid_argument("Unknown five-candidate variant");next_variant=v;next_count=v==1?4:v==2?2:6;next_mass=next_misses=0;next_rows=0;std::fill_n(next_events,3,0);next_ranked=0;}
extern "C" unsigned qwen_next_experts(){return next_count;}
extern "C" unsigned qwen_next_variant(){return next_variant;}
extern "C" bool qwen_next_refill_before_consume(){return next_variant==5;}
extern "C" void qwen_next_routing_stats(std::uint64_t*p){std::copy_n(next_events,3,p);p[3]=next_ranked;}
