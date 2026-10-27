// SPDX-License-Identifier: MIT
#pragma once
#include "split_bank_bridge.h"
namespace qwen_app {
// Eligibility only. The six strong owners and ready-wave roles separately
// grant writes/dispatch. Partial groups use the existing parameterized shader;
// no shader, weight type, activation type or reduction precision is changed.
inline bool split_bank_indexed_vector_layout(const ggml_tensor *out,std::size_t alignment) {
    if(!out||!out->src[0]||!out->src[1]||!out->src[2]||!alignment||
       alignment>bank_read_alignment||(alignment&(alignment-1)))return false;
    const auto *a=out->src[0],*b=out->src[1],*ids=out->src[2],*root=a->view_src;
    const auto k=a->ne[0],n=a->ne[1],count=ids->ne[0];
    if(!root||!split_bank_root_layout(root,0)||!a->buffer||root->buffer!=a->buffer||
       a->view_offs>=bank_read_alignment||a->view_offs%alignment||
       a->type!=GGML_TYPE_BF16||b->type!=GGML_TYPE_F32||ids->type!=GGML_TYPE_I32||out->type!=GGML_TYPE_F32||
       !((k==2560&&n==640)||(k==640&&n==2560))||
       (a->ne[2]!=26&&a->ne[2]!=27)||a->ne[3]!=1||a->nb[0]!=2||a->nb[1]!=std::size_t(k)*2||
       a->nb[2]!=padded_bank_stride||a->nb[3]!=padded_bank_stride*std::size_t(a->ne[2])||count<1||count>10||
       b->ne[0]!=k||(b->ne[1]!=1&&b->ne[1]!=count)||b->ne[2]!=1||b->ne[3]!=1||
       b->nb[0]!=4||b->nb[1]!=std::size_t(k)*4||
       ids->ne[1]!=1||ids->ne[2]!=1||ids->ne[3]!=1||ids->nb[0]!=4||ids->nb[1]!=std::size_t(count)*4||!ggml_is_contiguous(ids)||
       out->ne[0]!=n||out->ne[1]!=count||out->ne[2]!=1||out->ne[3]!=1||
       out->nb[0]!=4||out->nb[1]!=std::size_t(n)*4||!ggml_is_contiguous(out))return false;
    // The last exposed expert starts one plane before the physical tail. Its
    // residue plus payload must remain inside the actual byte-storage root.
    return a->view_offs+(std::size_t(a->ne[2])-1)*padded_bank_stride+bank_expert_bytes<=ggml_nbytes(root);
}
void configure_split_index_layout(bool,std::size_t descriptor_alignment=0);
}
