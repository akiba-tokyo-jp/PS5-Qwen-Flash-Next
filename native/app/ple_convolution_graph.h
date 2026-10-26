// SPDX-License-Identifier: MIT
#pragma once
#include "ple_slice_graph.h"
#include <array>
namespace qwen_app {
inline constexpr std::size_t PLE_fixture_channels=10240,PLE_fixture_guard=64,PLE_fixture_payload_cap=16u<<20;
struct PLEConvolutionGraph {
    ggml_tensor *output_root=nullptr,*result=nullptr;
    ggml_cgraph *graph=nullptr;
    unsigned CONT_nodes=0;
};
inline PLEConvolutionGraph build_PLE_convolution_fixture(ggml_context *context,ggml_tensor *padded,
        ggml_tensor *kernel,unsigned tokens,PLESliceMode mode) {
    // All input eligibility is checked by build_experimental_PLE_tap before
    // a graph can reach a backend. No operation changes the original tap sum.
    if(!context||!tokens||tokens>4)throw std::invalid_argument("Bounded PLE fixture context/width required");
    PLEConvolutionGraph out;
    out.output_root=ggml_new_tensor_1d(context,GGML_TYPE_F32,2*PLE_fixture_guard/4+tokens*PLE_fixture_channels);
    ggml_set_input(out.output_root);
    auto *target=ggml_view_2d(context,out.output_root,PLE_fixture_channels,tokens,PLE_fixture_channels*4,PLE_fixture_guard);
    ggml_tensor *sum=nullptr;
    for(unsigned k=0;k<4;++k) {
        const auto tap=build_experimental_PLE_tap(context,padded,kernel,tokens,k,mode);
        auto *term=ggml_mul(context,tap.shifted,tap.coefficient);sum=sum?ggml_add(context,sum,term):term;
    }
    out.result=ggml_cpy(context,ggml_silu(context,sum),target);ggml_set_output(out.result);
    out.graph=ggml_new_graph_custom(context,64,false);ggml_build_forward_expand(out.graph,out.result);
    for(int i=0;i<ggml_graph_n_nodes(out.graph);++i)out.CONT_nodes+=ggml_graph_node(out.graph,i)->op==GGML_OP_CONT;
    return out;
}
inline std::size_t PLE_fixture_context_bytes(){return ggml_tensor_overhead()*160+4*ggml_graph_overhead_custom(64,false);}
}
