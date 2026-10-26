// SPDX-License-Identifier: MIT
#include "ple_slice_graph.h"
#include <array>
#include <cmath>
#include <cstring>
#include <iostream>
#include <map>
#include <vector>
namespace {
void check(bool ok){if(!ok)throw std::runtime_error("PLE slice graph differs");}
// A deterministic tensor-address interpreter for the existing COPY/MUL graph.
// This checks actual GGML metadata; it does not execute a GPU/CPU backend.
class AddressFixture {
    std::map<ggml_tensor*,std::vector<unsigned char>> storage;
public:
    unsigned char *data(ggml_tensor *t) {
        if(t->view_src)return data(t->view_src)+t->view_offs;
        if(t->data)return static_cast<unsigned char*>(t->data);
        auto found=storage.find(t);if(found!=storage.end())return found->second.data();
        auto &out=storage[t];out.resize(ggml_nbytes(t));
        check(t->type==GGML_TYPE_F32||t->type==GGML_TYPE_BF16);
        for(std::int64_t y=0;y<t->ne[1];++y)for(std::int64_t x=0;x<t->ne[0];++x) {
            float value=0;
            if(t->op==GGML_OP_CONT||t->op==GGML_OP_CPY)value=get(t->src[0],x,y);
            else if(t->op==GGML_OP_MUL)value=get(t->src[0],x,y)*get(t->src[1],x%t->src[1]->ne[0],y%t->src[1]->ne[1]);
            else throw std::runtime_error("Unexpected fixture operation");
            auto *at=out.data()+x*t->nb[0]+y*t->nb[1];
            if(t->type==GGML_TYPE_F32)std::memcpy(at,&value,4);
            else {std::uint32_t bits;std::memcpy(&bits,&value,4);check(!(bits&65535));const auto b=std::uint16_t(bits>>16);std::memcpy(at,&b,2);}
        }
        return out.data();
    }
    float get(ggml_tensor *t,std::int64_t x,std::int64_t y) {
        const auto *p=data(t)+x*t->nb[0]+y*t->nb[1];float value;
        if(t->type==GGML_TYPE_F32)std::memcpy(&value,p,4);
        else {check(t->type==GGML_TYPE_BF16);std::uint16_t b;std::memcpy(&b,p,2);const std::uint32_t bits=std::uint32_t(b)<<16;std::memcpy(&value,&bits,4);}
        return value;
    }
};
}
int main() {
    unsigned graphs=0,values=0,refusals=0;std::array<unsigned,4> conts{};
    for(unsigned tokens:{1,2,3,4}) {
        std::vector<float> history((9+tokens)*10240);
        std::vector<std::uint16_t> weights(4*10240);
        for(std::size_t i=0;i<history.size();++i)history[i]=float(int(i%97)-48)/12288.0f;
        for(std::size_t i=0;i<weights.size();++i)weights[i]=std::uint16_t((i&1?0x8000:0)|0x3b00|((i*37)%1024));
        std::vector<float> reference;
        for(unsigned mode=0;mode<4;++mode) {
            auto *ctx=ggml_init({2u<<20,nullptr,true});check(ctx!=nullptr);
            auto *padded=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,9+tokens,10240,1);padded->data=history.data();
            auto *kernel=ggml_new_tensor_2d(ctx,GGML_TYPE_BF16,4,10240);kernel->data=weights.data();
            std::vector<float> result;AddressFixture fixture;
            for(unsigned k=0;k<4;++k) {
                const auto tap=qwen_app::build_experimental_PLE_tap(ctx,padded,kernel,tokens,k,static_cast<qwen_app::PLESliceMode>(mode));
                auto *product=ggml_mul(ctx,tap.shifted,tap.coefficient);auto *graph=ggml_new_graph_custom(ctx,32,false);
                ggml_build_forward_expand(graph,product);
                unsigned count=0,casts=0;
                for(int i=0;i<ggml_graph_n_nodes(graph);++i) {
                    const auto *node=ggml_graph_node(graph,i);count+=node->op==GGML_OP_CONT;casts+=node->op==GGML_OP_CPY;
                }
                check(count==2-unsigned(bool(mode&1))-unsigned(bool(mode&2))&&casts==1);conts[mode]+=count;
                if(mode&2)check(tap.shifted->nb[0]==(9+tokens)*4&&tap.shifted->nb[1]==4);
                for(unsigned y=0;y<tokens;++y)for(unsigned x=0;x<10240;++x) {
                    const float actual=fixture.get(product,x,y),w=fixture.get(kernel,k,x);
                    const float expected=float(double(history[x*(9+tokens)+k*3+y])*double(w));
                    check(actual==expected&&std::isfinite(actual));result.push_back(actual);++values;
                }
                ++graphs;
            }
            if(mode==0)reference=result;else check(reference.size()==result.size()&&std::memcmp(reference.data(),result.data(),result.size()*4)==0);
            for(unsigned invalid=0;invalid<4;++invalid) {
                try {
                    qwen_app::build_experimental_PLE_tap(invalid==0?nullptr:ctx,padded,kernel,
                        invalid==1?5:tokens,invalid==2?4:0,static_cast<qwen_app::PLESliceMode>(invalid==3?4:mode));
                    throw std::logic_error("Invalid graph accepted");
                }catch(const std::invalid_argument&){++refusals;}
            }
            ggml_free(ctx);
        }
    }
    check(graphs==64&&values==1638400&&refusals==64);
    std::cout<<"{\"actual_GGML_tap_graphs\":"<<graphs<<",\"exact_F32_values\":"<<values<<",\"refusals\":"<<refusals
        <<",\"CONT_nodes_by_mode\":["<<conts[0]<<','<<conts[1]<<','<<conts[2]<<','<<conts[3]
        <<"],\"BF16_to_F32_conversion_preserved\":true,\"backend_arithmetic_executed\":false,\"model_evaluation\":false}"<<std::endl;
}
