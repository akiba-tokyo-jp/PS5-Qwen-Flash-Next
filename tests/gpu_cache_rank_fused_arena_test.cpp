// SPDX-License-Identifier: MIT
#include "gpu_cache_rank_fused_graph.h"
#include <cassert>
#include <cstring>
#include <vector>
template<class F>void refused(F f){bool failed=false;try{f();}catch(const std::runtime_error&){failed=true;}assert(failed);}
int main(){
    for(unsigned tokens:{1u,2u}){
        auto*ctx=ggml_init({16u<<20,nullptr,false});assert(ctx);
        auto*storage=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,512,tokens,48);ggml_set_input(storage);
        auto*source=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,512,tokens);
        auto*raw=static_cast<float*>(storage->data);std::fill_n(raw,48*512*tokens,1.5f);
        std::vector<ggml_tensor*>outputs;
        for(unsigned layer=0;layer<48;++layer){
            auto*t=qwen_app::fused_rank_output(ctx,source,storage,layer);outputs.push_back(t);
            assert(t->op==GGML_OP_ARGSORT&&t->type==GGML_TYPE_I32&&t->src[0]==source&&t->src[1]==storage&&t->view_src==storage);
            assert(t->data==raw+layer*512*tokens&&t->view_offs==layer*512*tokens*sizeof(float));
            assert(ggml_nbytes(t)==512*tokens*sizeof(int32_t));
        }
        for(unsigned layer=0;layer<48;++layer){
            auto*t=outputs[layer];auto*ids=static_cast<int32_t*>(t->data);
            for(unsigned row=0;row<tokens;++row)for(unsigned i=0;i<512;++i)ids[row*512+i]=511-i;
            auto*top=ggml_view_4d(ctx,t,10,tokens,1,1,t->nb[1],t->nb[2],t->nb[3],0);
            assert(top->src[0]==t&&top->view_src==storage&&top->data==t->data);
            for(unsigned row=0;row<tokens;++row)for(unsigned i=0;i<10;++i)
                assert(*reinterpret_cast<int32_t*>(static_cast<char*>(top->data)+row*top->nb[1]+i*top->nb[0])==int32_t(511-i));
            if(layer<47)assert(raw[(layer+1)*512*tokens]==1.5f);
        }
        refused([&]{qwen_app::fused_rank_output(ctx,source,storage,48);});
        auto*shorter=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,512,tokens);ggml_set_input(shorter);
        refused([&]{qwen_app::fused_rank_output(ctx,source,shorter,0);});
        auto*wrong=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,511,tokens);
        refused([&]{qwen_app::fused_rank_output(ctx,wrong,storage,0);});
        storage->flags&=~GGML_TENSOR_FLAG_INPUT;
        refused([&]{qwen_app::fused_rank_output(ctx,source,storage,0);});
        ggml_free(ctx);
    }
}
