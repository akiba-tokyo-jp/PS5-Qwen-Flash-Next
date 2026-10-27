// SPDX-License-Identifier: MIT
#include "padded_bank_layout.h"
#include "padded_bank_bridge.h"
#include "padded_bank.h"
#include "padded_cache_geometry.h"
#include "indexed_vector.h"
#include "split_bank_route.h"
#include <atomic>
#include <stdexcept>
namespace {
std::atomic<bool> padded_route_enabled{false};
std::atomic<std::size_t> padded_descriptor_alignment{0};
std::atomic<bool> split_route_enabled{false};
std::atomic<std::size_t> split_descriptor_alignment{0};
}
namespace qwen_app {
void configure_padded_index_layout(bool enabled,std::size_t alignment) {
    if(enabled&&(!alignment||(alignment&(alignment-1))||alignment>bank_read_alignment))
        throw std::invalid_argument("Padded dispatch requires the real bounded descriptor alignment");
    padded_descriptor_alignment.store(alignment);padded_route_enabled.store(enabled);
}
void configure_split_index_layout(bool enabled,std::size_t alignment) {
    if(enabled&&(!alignment||(alignment&(alignment-1))||alignment>bank_read_alignment))
        throw std::invalid_argument("Split dispatch requires its actual bounded descriptor alignment");
    split_descriptor_alignment.store(alignment);split_route_enabled.store(enabled);
}
}
extern "C" bool qwen_app_padded_index_layout(const ggml_tensor *output) {
    if(split_route_enabled.load()&&qwen_app::split_bank_indexed_vector_layout(output,split_descriptor_alignment.load()))return true;
    if(!padded_route_enabled.load()||!output||!output->src[0])return false;
    const auto *a=output->src[0];const auto *root=a->view_src;
    const auto alignment=padded_descriptor_alignment.load();
    const auto geometry=qwen_app::selected_padded_cache_geometry();
    if(!root||root->view_src||root->view_offs||!a->buffer||!alignment||
       a->ne[2]!=static_cast<std::int64_t>(geometry.active_slots)||
       a->view_offs>=qwen_app::bank_read_alignment||a->view_offs%alignment||
       a->nb[2]!=qwen_app::padded_bank_stride||root->nb[2]!=qwen_app::padded_bank_stride||
       root->ne[2]!=static_cast<std::int64_t>(geometry.physical_slots())||root->type!=GGML_TYPE_BF16||
       root->ne[0]!=a->ne[0]||root->ne[1]!=a->ne[1]||root->ne[3]!=1||root->buffer!=a->buffer||
       root->nb[0]!=2||root->nb[1]!=std::size_t(a->ne[0])*2||
       root->nb[3]!=qwen_app::padded_bank_stride*geometry.physical_slots())return false;
    // Reuse the qualified predicate for every field except the padded plane
    // stride. These metadata copies never alter the graph or any tensor data.
    auto logical=*a;logical.nb[2]=qwen_app::bank_expert_bytes;logical.nb[3]=logical.nb[2]*logical.ne[2];
    // The complete 128-slot root/view was checked above. Normalize only this
    // local eligibility copy; actual tensor dimensions and validated IDs remain
    // unchanged for dispatch. The contiguous-tensor predicate stays unchanged.
    logical.ne[2]=qwen_app::padded_bank_active_slots;
    logical.nb[3]=logical.nb[2]*logical.ne[2];
    auto checked=*output;checked.src[0]=&logical;
    return qwen_app::bf16_indexed_vector_layout(&checked);
}
