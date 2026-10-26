// SPDX-License-Identifier: MIT
#include "ple_convolution_graph.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <iostream>
#include <map>
#include <vector>
namespace {
void check(bool ok){if(!ok)throw std::runtime_error("PLE convolution fixture metadata differs");}
// Executes only a deterministic address fixture over actual GGML metadata.
// In particular CPY may write a view, so evaluate nodes in graph order rather
// than treating every alias as an already completed value. No backend runs.
class Addresses {
    std::map<ggml_tensor*,std::vector<unsigned char>> storage;
    unsigned char *data(ggml_tensor *t) {
        if(t->view_src)return data(t->view_src)+t->view_offs;
        if(t->data)return static_cast<unsigned char*>(t->data);
        auto &bytes=storage[t];if(bytes.empty())bytes.resize(ggml_nbytes(t));return bytes.data();
    }
    float get(ggml_tensor *t,std::int64_t x,std::int64_t y) {
        const auto *p=data(t)+x*t->nb[0]+y*t->nb[1];float value;
        if(t->type==GGML_TYPE_F32)std::memcpy(&value,p,4);
        else {check(t->type==GGML_TYPE_BF16);std::uint16_t b;std::memcpy(&b,p,2);const std::uint32_t bits=std::uint32_t(b)<<16;std::memcpy(&value,&bits,4);}
        return value;
    }
public:
    void run(ggml_cgraph *graph) {
        for(int n=0;n<ggml_graph_n_nodes(graph);++n) {
            auto *t=ggml_graph_node(graph,n);
            if(t->op==GGML_OP_VIEW||t->op==GGML_OP_RESHAPE||t->op==GGML_OP_TRANSPOSE||t->op==GGML_OP_PERMUTE)continue;
            for(std::int64_t y=0;y<t->ne[1];++y)for(std::int64_t x=0;x<t->ne[0];++x) {
                float v=get(t->src[0],x,y);
                if(t->op==GGML_OP_MUL||t->op==GGML_OP_ADD) {
                    const auto *b=t->src[1];const float w=get(t->src[1],x%b->ne[0],y%b->ne[1]);v=t->op==GGML_OP_MUL?v*w:v+w;
                }else if(t->op==GGML_OP_UNARY) {check(ggml_get_unary_op(t)==GGML_UNARY_OP_SILU);v=v/(1.0f+std::exp(-v));}
                else check(t->op==GGML_OP_CPY||t->op==GGML_OP_CONT);
                auto *out=data(t)+x*t->nb[0]+y*t->nb[1];
                if(t->type==GGML_TYPE_F32)std::memcpy(out,&v,4);
                else {std::uint32_t bits;std::memcpy(&bits,&v,4);check(!(bits&65535));const auto b=std::uint16_t(bits>>16);std::memcpy(out,&b,2);}
            }
        }
    }
};
}
int main() {
    std::size_t maximum_raw=0,maximum_metadata=0;unsigned graphs=0,values=0;
    for(unsigned width=1;width<=4;++width) {
        constexpr auto guard=qwen_app::PLE_fixture_guard,channels=qwen_app::PLE_fixture_channels;
        std::vector<unsigned char> history(2*guard+(9+width)*channels*4,0xa7),kernel(2*guard+channels*4*2,0xa7);
        std::array<std::vector<unsigned char>,4> output;
        for(std::size_t i=0;i<(9+width)*channels;++i){const float value=float(int(i%97)-48)/12288.0f;std::memcpy(history.data()+guard+4*i,&value,4);}
        for(std::size_t i=0;i<4*channels;++i){const std::uint16_t b=std::uint16_t((i&1?0x8000:0)|0x3b00|((i*37)%1024));std::memcpy(kernel.data()+guard+2*i,&b,2);}
        auto *ctx=ggml_init({qwen_app::PLE_fixture_context_bytes(),nullptr,true});check(ctx);
        auto *hr=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,history.size()/4);auto *kr=ggml_new_tensor_1d(ctx,GGML_TYPE_BF16,kernel.size()/2);
        auto *padded=ggml_view_3d(ctx,hr,9+width,channels,1,(9+width)*4,(9+width)*channels*4,guard);
        auto *weights=ggml_view_2d(ctx,kr,4,channels,8,guard);hr->data=history.data();kr->data=kernel.data();
        std::vector<float> reference;
        for(unsigned mode=0;mode<4;++mode) {
            const auto built=qwen_app::build_PLE_convolution_fixture(ctx,padded,weights,width,static_cast<qwen_app::PLESliceMode>(mode));
            output[mode].assign(2*guard+width*channels*4,0xa7);built.output_root->data=output[mode].data();
            check(built.CONT_nodes==8-4*unsigned(bool(mode&1))-4*unsigned(bool(mode&2)));
            Addresses fixture;fixture.run(built.graph);std::vector<float> actual(width*channels);
            std::memcpy(actual.data(),output[mode].data()+guard,actual.size()*4);
            for(unsigned token=0;token<width;++token)for(unsigned channel=0;channel<channels;++channel) {
                double sum=0;
                for(unsigned k=0;k<4;++k) {
                    float input,weight;std::uint16_t b;std::memcpy(&input,history.data()+guard+4*(channel*(9+width)+k*3+token),4);
                    std::memcpy(&b,kernel.data()+guard+2*(channel*4+k),2);const std::uint32_t bits=std::uint32_t(b)<<16;std::memcpy(&weight,&bits,4);
                    sum+=double(input)*weight;
                }
                const auto expected=sum/(1.0+std::exp(-sum));const auto value=actual[token*channels+channel];
                check(std::isfinite(value)&&std::abs(value-expected)<=1e-5+1e-5*std::abs(expected));++values;
            }
            if(!mode)reference=actual;else check(!std::memcmp(reference.data(),actual.data(),actual.size()*4));
            for(unsigned i=0;i<guard;++i)check(output[mode][i]==0xa7&&output[mode][output[mode].size()-1-i]==0xa7);
            ++graphs;
        }
        std::size_t raw=0;
        for(auto *t=ggml_get_first_tensor(ctx);t;t=ggml_get_next_tensor(ctx,t))if(!t->view_src)raw+=ggml_nbytes(t);
        check(raw<=qwen_app::PLE_fixture_payload_cap);maximum_raw=std::max(maximum_raw,raw);maximum_metadata=std::max(maximum_metadata,ggml_used_mem(ctx));
        ggml_free(ctx);
    }
    check(graphs==16&&values==409600);
    std::cout<<"{\"actual_GGML_full_convolution_graphs\":"<<graphs<<",\"exact_F32_outputs\":"<<values
        <<",\"maximum_raw_root_bytes\":"<<maximum_raw<<",\"maximum_metadata_used_bytes\":"<<maximum_metadata
        <<",\"output_view_COPY_executed\":true,\"F64_reference_passed\":true,\"backend_execution\":false}"<<std::endl;
}
