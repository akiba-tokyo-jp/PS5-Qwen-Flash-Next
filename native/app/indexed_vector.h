// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include <cstdint>

namespace qwen_app {
// Limit the experimental route to the admitted Flash-Next expert bank layouts.
// IDs are already validated/remapped by the existing expert cache. This guard
// selects an existing shader and never changes weights, slots or GPU features.
inline bool bf16_indexed_vector_layout(const ggml_tensor * dst) {
    if (!dst || !dst->src[0] || !dst->src[1] || !dst->src[2]) return false;
    const auto * a=dst->src[0]; const auto * b=dst->src[1]; const auto * ids=dst->src[2];
    const auto k=a->ne[0], n=a->ne[1];
    return a->type==GGML_TYPE_BF16 && b->type==GGML_TYPE_F32 &&
        ids->type==GGML_TYPE_I32 && dst->type==GGML_TYPE_F32 &&
        ((k==2560 && n==640) || (k==640 && n==2560)) &&
        a->ne[2]>=10 && a->ne[2]<=53 && a->ne[3]==1 &&
        a->nb[0]==2 && a->nb[1]==std::uint64_t(k)*2 &&
        a->nb[2]==std::uint64_t(k)*n*2 &&
        b->ne[0]==k && (b->ne[1]==1 || b->ne[1]==10) && b->ne[2]==1 && b->ne[3]==1 &&
        b->nb[0]==4 && b->nb[1]==std::uint64_t(k)*4 &&
        ids->ne[0]==10 && ids->ne[1]==1 && ids->ne[2]==1 && ids->ne[3]==1 &&
        ids->nb[0]==4 && ids->nb[1]==40 &&
        dst->ne[0]==n && dst->ne[1]==10 && dst->ne[2]==1 && dst->ne[3]==1 &&
        dst->nb[0]==4 && dst->nb[1]==std::uint64_t(n)*4;
}

struct GpuPathStats {
    std::uint64_t bf16_matrix=0,bf16_vector=0,mapped_write_bytes=0,staging_write_bytes=0;
};
void configure_bf16_indexed_vector(bool);
void set_bf16_indexed_vector_scope(bool);
GpuPathStats gpu_path_stats();
}
extern "C" {
bool qwen_app_bf16_indexed_vector_enabled();
void qwen_app_record_bf16_indexed_path(bool);
void qwen_app_record_upload_path(bool,std::uint64_t);
}
