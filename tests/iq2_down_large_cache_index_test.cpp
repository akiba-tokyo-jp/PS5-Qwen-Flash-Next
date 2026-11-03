// SPDX-License-Identifier: MIT
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include "iq2_down_index_under_test.h"

static std::uint64_t cases=0,old_overflow_negatives=0;
static constexpr std::uint64_t planes=3713,values=1638400,bytes=460800;
static void check(std::uint32_t index,std::uint32_t units,std::uint32_t lane){
    const auto actual=iq2_down_plane_value(index,units,lane);
    const std::uint64_t global=std::uint64_t(index)*units+lane;
    const auto plane=global/values,logical=global%values;
    if(actual.x!=plane||actual.y!=logical||plane>=planes||logical>=values)std::abort();
    const std::uint64_t base=std::uint64_t(actual.x)*bytes;
    const auto payload=base+64+(actual.y/256)*66+65;
    const auto table=base+422464+2560-1;
    if(payload>=base+bytes||table>=base+bytes||table>=planes*bytes||table>std::numeric_limits<std::int32_t>::max())std::abort();
    const std::uint32_t old=index*units+lane;
    const bool old_wrong=old/values!=plane||old%values!=logical;
    if(old_wrong!=(global>std::numeric_limits<std::uint32_t>::max()))std::abort();
    old_overflow_negatives+=old_wrong;++cases;
}
int main(){
    const std::uint32_t boundaries[]={0,1,3,4,31,32,63,64,255,256,639,640,1279,1280,65535,65536,720895,720896,1638399};
    for(const auto units:{4u,64u}){
        const auto per=std::uint32_t(values/units);
        if((planes*per-1)>std::numeric_limits<std::uint32_t>::max()||
           std::uint64_t(per-1)*units+(units-1)!=values-1)std::abort();
        for(std::uint32_t plane=0;plane<planes;++plane)
            for(const auto scalar:boundaries)
                for(std::uint32_t lane=0;lane<units;++lane)check(plane*per+scalar/units,units,lane);
        for(const std::uint32_t plane:{0u,2620u,2621u,2622u,3711u,3712u})
            for(std::uint32_t local=0;local<per;++local)
                for(std::uint32_t lane=0;lane<units;++lane)check(plane*per+local,units,lane);
    }
    if(!old_overflow_negatives)std::abort();
    std::printf("{\"completed\":true,\"cases\":%llu,\"old_overflow_negatives\":%llu,\"planes\":3713,\"logical_elements\":6083379200,\"carrier_bytes\":1710950400}\n",
        static_cast<unsigned long long>(cases),static_cast<unsigned long long>(old_overflow_negatives));
}
