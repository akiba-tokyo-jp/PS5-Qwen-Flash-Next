// SPDX-License-Identifier: MIT
#pragma once
#include "llama-graph.h"
#include "llama-batch.h"
#include "ggml-backend.h"
#include <array>
#include <memory>
#include <stdexcept>

extern "C" void qwen_gpu_cache_rank_coefficients(unsigned,float*,std::size_t);
namespace qwen_app {
class GpuCacheRankInput final:public llm_graph_input_i {
public:
    ggml_tensor*coefficients=nullptr;
    unsigned layer=0,tokens=0;
    void set_input(const llama_ubatch*ubatch)override{
        if(!ubatch||unsigned(ubatch->n_tokens)!=tokens||!coefficients||ggml_nbytes(coefficients)!=512*sizeof(float))
            throw std::runtime_error("GPU rank input shape changed before publication");
        std::array<float,512> values{};
        qwen_gpu_cache_rank_coefficients(layer,values.data(),values.size());
        ggml_backend_tensor_set(coefficients,values.data(),0,sizeof(values));
    }
    bool can_reuse(const llm_graph_params&params)override{return unsigned(params.ubatch.n_tokens)==tokens;}
};
inline ggml_tensor*build_gpu_cache_rank(ggml_context*ctx,llm_graph_result*result,ggml_tensor*source,unsigned layer){
    if(!ctx||!result||!source||source->type!=GGML_TYPE_F32||source->ne[0]!=512||
       (source->ne[1]!=1&&source->ne[1]!=2)||source->ne[2]!=1||source->ne[3]!=1||layer>=48)
        throw std::runtime_error("GPU ranking requires one or two complete current probability rows");
    auto input=std::make_unique<GpuCacheRankInput>();input->layer=layer;input->tokens=unsigned(source->ne[1]);
    input->coefficients=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,512);ggml_set_input(input->coefficients);
    const auto weighted=ggml_mul(ctx,source,input->coefficients);result->add_input(std::move(input));return weighted;
}
}
