// SPDX-License-Identifier: MIT
#pragma once
#include "llama-graph.h"
#include "llama-batch.h"
#include "ggml-backend.h"
#include <array>
#include <memory>
#include <stdexcept>
#if QWEN_GPU_RANK_VALIDATE_BACKEND
#include <cstdio>
extern "C" void qwen_native_stage(const char*);
#endif

extern "C" void qwen_gpu_cache_rank_coefficients_all(float*,std::size_t);
namespace qwen_app {
class GpuCacheRankInput final:public llm_graph_input_i {
public:
    ggml_tensor*coefficients=nullptr;
    unsigned tokens=0;
    std::array<float,48*512> values{};
#if QWEN_GPU_RANK_VALIDATE_BACKEND
    ggml_tensor*weighted=nullptr;
    bool backend_observed=false;
#endif
    void set_input(const llama_ubatch*ubatch)override{
        if(!ubatch||unsigned(ubatch->n_tokens)!=tokens||!coefficients||ggml_nbytes(coefficients)!=48*512*sizeof(float))
            throw std::runtime_error("GPU rank input shape changed before publication");
        qwen_gpu_cache_rank_coefficients_all(values.data(),values.size());
        ggml_backend_tensor_set(coefficients,values.data(),0,sizeof(values));
#if QWEN_GPU_RANK_VALIDATE_BACKEND
        if(!backend_observed){
            const auto buffer=weighted?weighted->buffer:nullptr;
            const auto type=buffer?ggml_backend_buffer_get_type(buffer):nullptr;
            const auto device=type?ggml_backend_buft_get_device(type):nullptr;
            char text[200];std::snprintf(text,sizeof(text),"G1_backend layer=0 result_device_type=%d result_buffer=%.64s rows=%u",
                device?int(ggml_backend_dev_type(device)):-1,buffer?ggml_backend_buffer_name(buffer):"missing",tokens);
            qwen_native_stage(text);backend_observed=true;
        }
#endif
    }
    bool can_reuse(const llm_graph_params&params)override{return unsigned(params.ubatch.n_tokens)==tokens;}
};
inline ggml_tensor*build_gpu_cache_rank(ggml_context*ctx,llm_graph_result*result,ggml_tensor*source,unsigned layer){
    if(!ctx||!result||!source||source->type!=GGML_TYPE_F32||source->ne[0]!=512||
       (source->ne[1]!=1&&source->ne[1]!=2)||source->ne[2]!=1||source->ne[3]!=1||layer>=48)
        throw std::runtime_error("GPU ranking requires one or two complete current probability rows");
    GpuCacheRankInput*input=nullptr;
    for(auto&existing:result->inputs)if(auto*match=dynamic_cast<GpuCacheRankInput*>(existing.get())){input=match;break;}
    if(!input){
        auto owned=std::make_unique<GpuCacheRankInput>();owned->tokens=unsigned(source->ne[1]);
        owned->coefficients=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,512,48);ggml_set_input(owned->coefficients);
        input=static_cast<GpuCacheRankInput*>(result->add_input(std::move(owned)));
    }
    if(input->tokens!=unsigned(source->ne[1]))throw std::runtime_error("One ranking matrix must serve one complete decode graph");
    const auto row=ggml_view_1d(ctx,input->coefficients,512,std::size_t(layer)*512*sizeof(float));
    const auto weighted=ggml_mul(ctx,source,row);
#if QWEN_GPU_RANK_VALIDATE_BACKEND
    if(layer==0)input->weighted=weighted;
#endif
    return weighted;
}
}
