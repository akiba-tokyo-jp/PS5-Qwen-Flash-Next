// SPDX-License-Identifier: MIT
#pragma once
#include "expert_q2_sparse.h"
#include <algorithm>
#include <vector>
#include <stdexcept>
namespace qwen_app {
inline std::vector<ExpertQ2SourceSegment> relocate_source_range(const std::vector<ExpertQ2SourceSegment>&parent,
        std::uint64_t original,std::uint64_t bytes,std::uint64_t destination){
    if(!bytes||original>UINT64_MAX-bytes||destination>UINT64_MAX-bytes)throw std::invalid_argument("Invalid source relocation range");
    std::vector<ExpertQ2SourceSegment>out;std::uint64_t copied=0;
    for(const auto&s:parent){
        if(s.logical_offset>UINT64_MAX-s.bytes)throw std::invalid_argument("Parent source range overflows");
        const auto lo=std::max(original,s.logical_offset),hi=std::min(original+bytes,s.logical_offset+s.bytes);
        if(lo>=hi)continue;if(lo!=original+copied)throw std::invalid_argument("Relocated parent range is incomplete");
        out.push_back({destination+copied,hi-lo,s.physical,s.physical_offset+lo-s.logical_offset});copied+=hi-lo;
    }if(copied!=bytes)throw std::invalid_argument("Relocated source bytes are missing");return out;
}
// Overlay only bounded owned ranges; unconsumed parent tails remain intact.
inline std::vector<ExpertQ2SourceSegment> merge_source_overlays(
        const std::vector<ExpertQ2SourceSegment>&parent,std::vector<ExpertQ2SourceSegment>overlays,std::uint64_t total){
    std::sort(overlays.begin(),overlays.end(),[](const auto&a,const auto&b){return a.logical_offset<b.logical_offset;});
    std::uint64_t end=0;for(const auto&s:parent){if(s.logical_offset!=end||!s.bytes||s.bytes>total-end)throw std::invalid_argument("Incomplete parent source coverage");end+=s.bytes;}
    if(end!=total)throw std::invalid_argument("Parent source length differs");end=0;
    for(const auto&s:overlays){if(!s.bytes||s.logical_offset<end||s.logical_offset>total||s.bytes>total-s.logical_offset)throw std::invalid_argument("Source overlays overlap or exceed their parent");end=s.logical_offset+s.bytes;}
    std::vector<ExpertQ2SourceSegment>out;std::size_t pi=0,oi=0;std::uint64_t at=0;
    while(at<total){
        if(oi<overlays.size()&&overlays[oi].logical_offset==at){out.push_back(overlays[oi]);at+=overlays[oi++].bytes;continue;}
        while(pi<parent.size()&&parent[pi].logical_offset+parent[pi].bytes<=at)++pi;
        if(pi==parent.size()||parent[pi].logical_offset>at)throw std::invalid_argument("Parent source has a gap");
        const auto&s=parent[pi];const auto stop=std::min(s.logical_offset+s.bytes,oi<overlays.size()?overlays[oi].logical_offset:total);
        if(stop<=at)throw std::logic_error("Source overlay did not advance");
        out.push_back({at,stop-at,s.physical,s.physical_offset+at-s.logical_offset});at=stop;
    }return out;
}
}
