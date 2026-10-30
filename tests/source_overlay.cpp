// SPDX-License-Identifier: MIT
#include "source_overlay.h"
#include <iostream>
#include <array>
using namespace qwen_app;
void check(bool b){if(!b)throw std::runtime_error("Overlay check failed");}
int main(){try{
    const std::vector<ExpertQ2SourceSegment>base{{0,100,0,1000},{100,100,1,2000},{200,100,2,3000}};
    const std::vector<ExpertQ2SourceSegment>changes{{0,13,3,4000},{90,30,3,5000},{250,15,3,6000}};
    const auto out=merge_source_overlays(base,changes,300);std::uint64_t cursor=0;
    for(const auto&s:out){check(s.logical_offset==cursor);for(std::uint64_t i=0;i<s.bytes;++i){const auto at=cursor+i;
        const auto c=std::find_if(changes.begin(),changes.end(),[&](const auto&v){return at>=v.logical_offset&&at<v.logical_offset+v.bytes;});
        const auto p=std::find_if(base.begin(),base.end(),[&](const auto&v){return at>=v.logical_offset&&at<v.logical_offset+v.bytes;});
        const auto&e=c==changes.end()?*p:*c;check(s.physical==e.physical&&s.physical_offset+i==e.physical_offset+at-e.logical_offset);
    }cursor+=s.bytes;}check(cursor==300);
    unsigned rejected=0;for(unsigned mode=0;mode<4;++mode){auto p=base,o=changes;
        if(!mode)o.push_back({12,8,3,7000});if(mode==1)o.push_back({299,2,3,7000});if(mode==2)p[1].logical_offset=101;if(mode==3)o[0].bytes=0;
        try{merge_source_overlays(p,o,300);}catch(const std::exception&){++rejected;}}
    check(rejected==4);std::cout<<"Header replacement, cross-part payloads, unused tails and invalid overlays passed.\n";
    const auto shifted=relocate_source_range(base,90,150,20);cursor=20;for(const auto&s:shifted){check(s.logical_offset==cursor);for(std::uint64_t i=0;i<s.bytes;++i){const auto at=90+cursor-20+i;const auto&p=base[at/100];check(s.physical==p.physical&&s.physical_offset+i==p.physical_offset+at-p.logical_offset);}cursor+=s.bytes;}check(cursor==170);
}catch(const std::exception&e){std::cerr<<e.what();return 1;}}
