// SPDX-License-Identifier: MIT
#pragma once
#include "llama-graph.h"
#include "llama-batch.h"
#include "ggml-backend.h"
#include <array>
#include <cstring>
#include <memory>
#include <stdexcept>
#include <vector>
extern "C" bool qwen_app_route_is_decode();
extern "C" unsigned qwen_app_route_mode();
extern "C" void qwen_gpu_cache_rank_coefficients_all(float*,std::size_t);
namespace qwen_app {
inline bool fused_rank_device_type(enum ggml_backend_dev_type type){
    return type==GGML_BACKEND_DEVICE_TYPE_GPU||type==GGML_BACKEND_DEVICE_TYPE_IGPU;
}
inline ggml_tensor*fused_rank_output(ggml_context*ctx,ggml_tensor*source,ggml_tensor*storage,unsigned layer){
    if(!ctx||!source||!storage||source->type!=GGML_TYPE_F32||storage->type!=GGML_TYPE_F32||
       source->ne[0]!=512||source->ne[1]<1||source->ne[1]>2||source->ne[2]!=1||source->ne[3]!=1||layer>=48||
       ggml_nelements(storage)!=48*512*source->ne[1]||!(storage->flags&GGML_TENSOR_FLAG_INPUT))
        throw std::runtime_error("A complete protected coefficient/output arena is required");
    const auto offset=std::size_t(layer)*512*source->ne[1]*sizeof(float);
    auto*sorted=ggml_view_2d(ctx,storage,512,source->ne[1],512*sizeof(float),offset);
    sorted->type=GGML_TYPE_I32;sorted->op=GGML_OP_ARGSORT;sorted->src[0]=source;sorted->src[1]=storage;
    const int32_t order=GGML_SORT_ORDER_DESC;std::memcpy(sorted->op_params,&order,sizeof(order));
    return sorted;
}
class FusedCacheRankInput final:public llm_graph_input_i {
public:
    ggml_tensor*storage=nullptr;
    ggml_backend_t backend=nullptr;
    unsigned tokens=0,mode=0;
    bool decode=false,rank=false;
    std::array<float,48*512> coefficients{};
    std::vector<float> upload;
    std::array<bool,48> bound{};
    void set_input(const llama_ubatch*batch)override{
        if(!batch||unsigned(batch->n_tokens)!=tokens||!storage||upload.size()!=48*512*tokens||
           mode!=qwen_app_route_mode()||decode!=qwen_app_route_is_decode()||
           !storage->buffer||ggml_backend_buft_get_device(ggml_backend_buffer_get_type(storage->buffer))!=ggml_backend_get_device(backend))
            throw std::runtime_error("One live GPU coefficient/output arena with the original phase is required");
        if(rank)qwen_gpu_cache_rank_coefficients_all(coefficients.data(),coefficients.size());
        else coefficients.fill(1.f);
        for(unsigned layer=0;layer<48;++layer)for(unsigned row=0;row<tokens;++row)
            std::memcpy(upload.data()+(layer*tokens+row)*512,coefficients.data()+layer*512,512*sizeof(float));
        // One publication initializes every disjoint output view before any
        // compute. Input ownership prevents the graph allocator reusing it.
        ggml_backend_tensor_set(storage,upload.data(),0,upload.size()*sizeof(float));
    }
    bool can_reuse(const llm_graph_params&params)override{
        return unsigned(params.ubatch.n_tokens)==tokens&&mode==qwen_app_route_mode()&&decode==qwen_app_route_is_decode();
    }
};
inline ggml_tensor*fused_cache_rank_top_k(ggml_context*ctx,llm_graph_result*result,ggml_backend_sched_t sched,
    ggml_tensor*source,int used,unsigned layer,bool rank){
    if(!source)throw std::runtime_error("A complete original ranking input is required");
    if(source->ne[0]!=512||source->ne[1]>2)return ggml_argsort_top_k(ctx,source,used);
    if(!ctx||!result||!sched||source->type!=GGML_TYPE_F32||source->ne[1]<1||source->ne[2]!=1||source->ne[3]!=1||layer>=48)
        throw std::runtime_error("Fused ranking requires the current512-column trunk geometry");
    FusedCacheRankInput*input=nullptr;
    for(auto&candidate:result->inputs)if(auto*match=dynamic_cast<FusedCacheRankInput*>(candidate.get())){input=match;break;}
    if(!input){
        auto owned=std::make_unique<FusedCacheRankInput>();owned->tokens=unsigned(source->ne[1]);
        owned->mode=qwen_app_route_mode();owned->decode=qwen_app_route_is_decode();owned->rank=rank;
        for(int i=0;i<ggml_backend_sched_get_n_backends(sched);++i){
            auto b=ggml_backend_sched_get_backend(sched,i);
            if(fused_rank_device_type(ggml_backend_dev_type(ggml_backend_get_device(b)))){
                if(owned->backend)throw std::runtime_error("One Vulkan GPU backend is required for fused ranking");owned->backend=b;
            }
        }
        if(!owned->backend)throw std::runtime_error("A real GPU backend is required; no CPU fused-sort fallback");
        owned->storage=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,512,owned->tokens,48);ggml_set_input(owned->storage);
        owned->upload.resize(48*512*owned->tokens);
        ggml_backend_sched_set_tensor_backend(sched,owned->storage,owned->backend);
        input=static_cast<FusedCacheRankInput*>(result->add_input(std::move(owned)));
    }
    if(input->rank!=rank||input->tokens!=unsigned(source->ne[1])||input->bound[layer])
        throw std::runtime_error("Each current layer needs one disjoint original-phase sort output");
    auto*sorted=fused_rank_output(ctx,source,input->storage,layer);
    if(!ggml_backend_supports_op(input->backend,sorted))throw std::runtime_error("The selected GPU must support the complete original argsort");
    ggml_backend_sched_set_tensor_backend(sched,sorted,input->backend);input->bound[layer]=true;
    return ggml_view_4d(ctx,sorted,used,source->ne[1],source->ne[2],source->ne[3],sorted->nb[1],sorted->nb[2],sorted->nb[3],0);
}
}
