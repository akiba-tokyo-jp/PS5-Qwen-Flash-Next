// SPDX-License-Identifier: MIT
#include "delivery_overlap_plan.h"
#include <iostream>
#include <memory>
int main(){try{
    if(qwen_app::overlaps({0x1000,4096,1},{0x1000,4096,2})||!qwen_app::overlaps({0x1000,4096,1},{0x1800,4096,1})||!qwen_app::overlaps({0x1000,4096},{0x1800,4096}))throw std::runtime_error("Buffer address-space identity differs");
    auto p=std::make_unique<qwen_app::DeliveryOverlapPlan>();
    for(unsigned i=0;i<4;++i){p->nodes[i].pure=true;p->nodes[i].output={0x10000+i*4096,4096};}
    p->nodes[1].inputs[0]=0;p->nodes[3].inputs[0]=1;p->nodes[3].inputs[1]=2;
    using D=qwen_app::DeliveryOverlapPlan::Decision;
    if(p->inspect(4,1)!=D::ready||!p->selected[0]||!p->selected[1]||p->selected[2])throw std::runtime_error("Independent closure differs");
    p->nodes[2].external[0]=p->nodes[0].output;if(p->inspect(4,1)!=D::live_input_alias)throw std::runtime_error("Live input alias accepted");p->nodes[2].external[0]={};
    p->nodes[2].output=p->nodes[1].output;if(p->inspect(4,1)!=D::live_output_alias)throw std::runtime_error("Future output alias accepted");p->nodes[2].output={0x12000,4096};
    p->nodes[3].output=p->nodes[1].output;p->nodes[3].inplace=true;if(p->inspect(4,1)!=D::ready)throw std::runtime_error("Existing final-consumer in-place operation refused");
    p->nodes[0].pure=false;if(p->inspect(4,1)!=D::side_effect)throw std::runtime_error("Side effect accepted");p->nodes[0].pure=true;
    p->nodes[0].inputs[0]=2;if(p->inspect(4,1)!=D::dependency)throw std::runtime_error("Forward dependency accepted");
    *p=qwen_app::DeliveryOverlapPlan{};
    for(unsigned i=0;i<5;++i){p->nodes[i].pure=true;p->nodes[i].output={0x20000+i*4096,4096};}
    p->nodes[0].writes=false;p->nodes[1].writes=false;p->nodes[1].inputs[0]=0;p->nodes[1].output=p->nodes[0].output;
    p->nodes[2].inputs[0]=0;p->nodes[2].output=p->nodes[0].output;p->nodes[3].inputs[0]=1;p->nodes[4].inputs[0]=2;
    if(p->inspect(5,2)!=D::live_input_alias)throw std::runtime_error("Imported in-graph view alias accepted");
    p->nodes[2].output={0x22000,4096};if(p->inspect(5,2)!=D::ready)throw std::runtime_error("Disjoint imported view refused");
    std::cout<<"PASS: independent dependency closure, live input/output refusal, final in-place consumer and side effects\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
