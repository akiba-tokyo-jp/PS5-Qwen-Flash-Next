// SPDX-License-Identifier: MIT
#include "ready_expert_graph.h"
#include "split_padded_bank.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <iostream>
#include <map>
#include <vector>
namespace {void check(bool ok){if(!ok)throw std::runtime_error("Ready-expert graph qualification differs");}}
int main() {
    unsigned graphs=0,refused=0,values=0;
    for(unsigned count=1;count<=10;++count)for(unsigned group=0;group<2;++group) {
        auto *ctx=ggml_init({2u<<20,nullptr,true});check(ctx);
        const auto root_bytes=qwen_app::split_bank_planes[group]*qwen_app::padded_bank_stride;
        std::array<ggml_tensor *,3> roots{};
        for(auto &root:roots)root=ggml_new_tensor_1d(ctx,GGML_TYPE_BF16,root_bytes/2);
        qwen_app::ReadyExpertGraphInputs a;
        a.activation=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,2560,1,1);
        a.gate=ggml_view_3d(ctx,roots[0],2560,640,qwen_app::split_bank_active[group],5120,qwen_app::padded_bank_stride,32);
        a.up=ggml_view_3d(ctx,roots[1],2560,640,qwen_app::split_bank_active[group],5120,qwen_app::padded_bank_stride,32);
        a.down=ggml_view_3d(ctx,roots[2],640,2560,qwen_app::split_bank_active[group],1280,qwen_app::padded_bank_stride,32);
        a.slots=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,count,1);
        a.weights=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,1,count,1);
        a.contributions=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,10);a.count=count;
        for(unsigned i=0;i<count;++i)a.original_ordinals[i]=9-i;
        const auto build=[&](){return qwen_app::build_ready_expert_graph(ctx,a);};auto *graph=build();
        unsigned mm=0,glu=0,mul=0,copies=0;
        for(int n=0;n<ggml_graph_n_nodes(graph);++n) {
            auto *t=ggml_graph_node(graph,n);
            if(t->op==GGML_OP_MUL_MAT_ID){check(t->type==GGML_TYPE_F32&&t->src[0]->type==GGML_TYPE_BF16&&t->src[2]==a.slots);++mm;}
            if(t->op==GGML_OP_GLU){check(ggml_get_glu_op(t)==GGML_GLU_OP_SWIGLU);++glu;}
            if(t->op==GGML_OP_MUL){check(t->src[1]==a.weights);++mul;}
            if(t->op==GGML_OP_CPY) {
                check(t->view_src==a.contributions&&t->view_offs==a.original_ordinals[copies]*2560*4);
                check(t->src[0]->view_offs==copies*2560*4);++copies;
            }
        }
        check(mm==3&&glu==1&&mul==1&&copies==count);++graphs;
        const auto bad=[&](){try{build();}catch(const std::invalid_argument &){++refused;return;}throw std::runtime_error("Invalid ready graph accepted");};
        a.count=0;bad();a.count=count;
        a.original_ordinals[0]=10;bad();a.original_ordinals[0]=9;
        if(count>1){a.original_ordinals[1]=9;bad();a.original_ordinals[1]=8;}
        a.activation->type=GGML_TYPE_BF16;bad();a.activation->type=GGML_TYPE_F32;
        a.down->ne[0]=641;bad();a.down->ne[0]=640;
        a.slots->ne[0]=11;bad();a.slots->ne[0]=count;
        a.weights->ne[1]=11;bad();a.weights->ne[1]=count;
        ggml_free(ctx);
    }
    // Execute actual GGML reduction metadata with cancellation-sensitive F32
    // values. A bank-grouped or tree sum must not replace the original order.
    auto *ctx=ggml_init({2u<<20,nullptr,true});check(ctx);
    std::vector<float> input(2560*10+32,123.25f),output(2560+32,123.25f);
    auto *ir=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,input.size());ir->data=input.data();
    auto *orr=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,output.size());orr->data=output.data();
    auto *contributions=ggml_view_2d(ctx,ir,2560,10,2560*4,64);
    auto *out=ggml_view_2d(ctx,orr,2560,1,2560*4,64);
    for(unsigned i=0;i<10;++i)for(unsigned x=0;x<2560;++x)
        input[16+i*2560+x]=i==0?16777216.0f:i==1?1.0f:i==2?-16777216.0f:float((x+i)%7)/8;
    auto *graph=qwen_app::build_ready_expert_reduction(ctx,contributions,out);
    std::map<ggml_tensor *,std::vector<float>> temporary;
    const auto address=[&](auto &&self,ggml_tensor *t)->float * {
        if(t->view_src)return self(self,t->view_src)+t->view_offs/4;
        if(t->data)return static_cast<float *>(t->data);
        auto &data=temporary[t];if(data.empty())data.resize(ggml_nelements(t));return data.data();
    };
    unsigned adds=0;
    for(int n=0;n<ggml_graph_n_nodes(graph);++n) {
        auto *t=ggml_graph_node(graph,n);if(t->op==GGML_OP_VIEW)continue;
        auto *dst=address(address,t);const auto *first=address(address,t->src[0]);
        if(t->op==GGML_OP_ADD){const auto *second=address(address,t->src[1]);for(unsigned x=0;x<2560;++x)dst[x]=first[x]+second[x];++adds;}
        else {check(t->op==GGML_OP_CPY);std::copy(first,first+2560,dst);}
    }
    check(adds==9);
    for(unsigned x=0;x<2560;++x){float sum=input[16+x];for(unsigned i=1;i<10;++i)sum+=input[16+i*2560+x];check(output[16+x]==sum);++values;}
    for(unsigned i=0;i<16;++i)check(output[i]==123.25f&&output[output.size()-1-i]==123.25f);
    ggml_free(ctx);
    std::cout<<"{\"actual_GGML_partial_expert_graphs\":"<<graphs<<",\"partial_widths\":10,\"refusals\":"<<refused
        <<",\"original_order_F32_reduction_values\":"<<values<<",\"BF16_matrix_arithmetic_executed\":false,\"GPU_execution\":false}"<<std::endl;
}
