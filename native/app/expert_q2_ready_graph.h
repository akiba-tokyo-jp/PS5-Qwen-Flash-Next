// SPDX-License-Identifier: MIT
#pragma once
#include <ready_expert_graph.h>
namespace qwen_app {
// Separate quantized scope; preserve the original BF16 ready-graph guard.
inline ggml_cgraph*build_Q2_ready_expert_graph(ggml_context*ctx,const ReadyExpertGraphInputs&a){
    const auto matrix=[](const ggml_tensor*t,ggml_type type,int x,int y){return t&&t->type==type&&t->ne[0]==x&&t->ne[1]==y&&t->ne[3]==1&&ggml_is_contiguous(t);};
    if(!ctx||a.count!=5||!matrix(a.activation,GGML_TYPE_F32,2560,1)||a.activation->ne[2]!=1||
       !matrix(a.gate,GGML_TYPE_Q2_K,2560,640)||!matrix(a.up,GGML_TYPE_Q2_K,2560,640)||
       !matrix(a.down,GGML_TYPE_Q2_0,640,2560)||a.gate->ne[2]!=5||a.up->ne[2]!=5||a.down->ne[2]!=5||
       !matrix(a.slots,GGML_TYPE_I32,5,1)||!matrix(a.weights,GGML_TYPE_F32,1,5)||
       !matrix(a.contributions,GGML_TYPE_F32,2560,10))throw std::invalid_argument("Exact separate Q2 five-Expert wave required");
    std::array<bool,10>seen{};for(unsigned i=0;i<5;++i){const auto o=a.original_ordinals[i];if(o>=10||seen[o])throw std::invalid_argument("Unique original Q2 contribution ordinal required");seen[o]=true;}
    auto*up=ggml_mul_mat_id(ctx,a.up,a.activation,a.slots);auto*gate=ggml_mul_mat_id(ctx,a.gate,a.activation,a.slots);
    auto*activated=ggml_swiglu_split(ctx,gate,up);auto*down=ggml_mul_mat_id(ctx,a.down,activated,a.slots);auto*weighted=ggml_mul(ctx,down,a.weights);
    auto*g=ggml_new_graph_custom(ctx,128,false);
    for(unsigned i=0;i<5;++i){auto*source=ggml_view_2d(ctx,weighted,2560,1,weighted->nb[2],i*weighted->nb[1]);
        auto*destination=ggml_view_2d(ctx,a.contributions,2560,1,a.contributions->nb[1],a.original_ordinals[i]*a.contributions->nb[1]);
        ggml_build_forward_expand(g,ggml_cpy(ctx,source,destination));}return g;
}
inline ggml_cgraph*build_Q2_serial_ready_graph(ggml_context*ctx,const std::array<ReadyExpertGraphInputs,2>&groups,ggml_tensor*output){
    if(groups[0].activation!=groups[1].activation||groups[0].contributions!=groups[1].contributions)throw std::invalid_argument("Shared Q2 activation and contribution owner required");
    std::array<bool,10>seen{};for(const auto&a:groups)for(unsigned i=0;i<a.count;++i){const auto o=a.original_ordinals[i];if(o>=10||seen[o])throw std::invalid_argument("Complete distinct Q2 top-ten contributions required");seen[o]=true;}
    for(bool b:seen)if(!b)throw std::invalid_argument("All ten Q2 contributions required");
    auto*g=ggml_new_graph_custom(ctx,256,false);
    for(const auto&a:groups){auto*p=build_Q2_ready_expert_graph(ctx,a);for(int i=0;i<ggml_graph_n_nodes(p);++i)ggml_build_forward_expand(g,ggml_graph_node(p,i));}
    auto*r=build_ready_expert_reduction(ctx,groups[0].contributions,output);for(int i=0;i<ggml_graph_n_nodes(r);++i)ggml_build_forward_expand(g,ggml_graph_node(r,i));return g;
}
}
