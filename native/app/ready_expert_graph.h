// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include <array>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
struct ReadyExpertGraphInputs {
    ggml_tensor *activation=nullptr,*gate=nullptr,*up=nullptr,*down=nullptr;
    ggml_tensor *slots=nullptr,*weights=nullptr,*contributions=nullptr;
    std::array<unsigned,10> original_ordinals{};
    unsigned count=0;
};
// A partial original-precision graph only. This does not confer CPU write or
// GPU ownership: the caller must first admit the whole-expert ready wave and
// retain every backing owner through its matching positive completion epoch.
inline ggml_cgraph *build_ready_expert_graph(ggml_context *ctx,const ReadyExpertGraphInputs &a) {
    if(!ctx||!a.activation||!a.gate||!a.up||!a.down||!a.slots||!a.weights||!a.contributions||!a.count||a.count>10)
        throw std::invalid_argument("Bounded ready-expert graph inputs are required");
    const auto matrix=[](const ggml_tensor *t,ggml_type type,std::int64_t x,std::int64_t y) {
        return t->type==type&&t->ne[0]==x&&t->ne[1]==y&&t->ne[3]==1;
    };
    if(!matrix(a.activation,GGML_TYPE_F32,2560,1)||a.activation->ne[2]!=1||!ggml_is_contiguous(a.activation)||
       !matrix(a.gate,GGML_TYPE_BF16,2560,640)||!matrix(a.up,GGML_TYPE_BF16,2560,640)||
       !matrix(a.down,GGML_TYPE_BF16,640,2560)||a.gate->ne[2]!=a.up->ne[2]||a.gate->ne[2]!=a.down->ne[2]||
       a.gate->ne[2]<1||a.gate->ne[2]>53||
       !matrix(a.slots,GGML_TYPE_I32,a.count,1)||a.slots->ne[2]!=1||!ggml_is_contiguous(a.slots)||
       !matrix(a.weights,GGML_TYPE_F32,1,a.count)||a.weights->ne[2]!=1||!ggml_is_contiguous(a.weights)||
       !matrix(a.contributions,GGML_TYPE_F32,2560,10)||a.contributions->ne[2]!=1||!ggml_is_contiguous(a.contributions))
        throw std::invalid_argument("Ready graph requires original BF16 weights and single-token F32 top-ten geometry");
    std::array<bool,10> seen{};
    for(unsigned i=0;i<a.count;++i) {
        const auto ordinal=a.original_ordinals[i];
        if(ordinal>=10||seen[ordinal])throw std::invalid_argument("Each partial contribution requires a distinct original ordinal");
        seen[ordinal]=true;
    }
    // Match build_moe_ffn: independent up/gate projections, original SwiGLU,
    // down projection and route weighting before the original left-fold sum.
    auto *up=ggml_mul_mat_id(ctx,a.up,a.activation,a.slots);
    auto *gate=ggml_mul_mat_id(ctx,a.gate,a.activation,a.slots);
    auto *activated=ggml_swiglu_split(ctx,gate,up);
    auto *down=ggml_mul_mat_id(ctx,a.down,activated,a.slots);
    auto *weighted=ggml_mul(ctx,down,a.weights);
    auto *graph=ggml_new_graph_custom(ctx,128,false);
    for(unsigned i=0;i<a.count;++i) {
        auto *source=ggml_view_2d(ctx,weighted,2560,1,weighted->nb[2],i*weighted->nb[1]);
        auto *destination=ggml_view_2d(ctx,a.contributions,2560,1,a.contributions->nb[1],a.original_ordinals[i]*a.contributions->nb[1]);
        ggml_build_forward_expand(graph,ggml_cpy(ctx,source,destination));
    }
    return graph;
}
inline ggml_cgraph *build_ready_expert_reduction(ggml_context *ctx,ggml_tensor *contributions,ggml_tensor *output) {
    if(!ctx||!contributions||!output||contributions->type!=GGML_TYPE_F32||output->type!=GGML_TYPE_F32||
       contributions->ne[0]!=2560||contributions->ne[1]!=10||contributions->ne[2]!=1||contributions->ne[3]!=1||
       output->ne[0]!=2560||output->ne[1]!=1||output->ne[2]!=1||output->ne[3]!=1||
       !ggml_is_contiguous(contributions)||!ggml_is_contiguous(output))
        throw std::invalid_argument("Original top-ten reduction requires complete F32 contributions and output");
    auto *graph=ggml_new_graph_custom(ctx,64,false);
    std::array<ggml_tensor *,10> ordered{};
    for(unsigned i=0;i<10;++i) {
        ordered[i]=ggml_view_2d(ctx,contributions,2560,1,contributions->nb[1],i*contributions->nb[1]);
        ggml_build_forward_expand(graph,ordered[i]);
    }
    auto *sum=ordered[0];
    for(unsigned i=1;i<10;++i){sum=ggml_add(ctx,sum,ordered[i]);ggml_build_forward_expand(graph,sum);}
    ggml_build_forward_expand(graph,ggml_cpy(ctx,sum,output));return graph;
}
}
