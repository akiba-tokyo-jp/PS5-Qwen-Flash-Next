// SPDX-License-Identifier: MIT
#pragma once
#include "split_padded_bank.h"
#include "ggml.h"
#include <cstddef>
#include <cstdint>
namespace qwen_app {
// Separate experimental ABI. The qualified three-dimensional production-bank
// predicate is unchanged. This layout alone does not authorize a CPU write.
inline bool split_bank_root_layout(const ggml_tensor *t,unsigned group) {
    const auto bytes=split_bank_planes[0]*padded_bank_stride;
    return t&&group<2&&!t->view_src&&!t->view_offs&&t->type==GGML_TYPE_BF16&&
        t->ne[0]==std::int64_t(bytes/2)&&t->ne[1]==1&&t->ne[2]==1&&t->ne[3]==1&&
        ggml_is_contiguous(t)&&ggml_nbytes(t)==bytes;
}
struct SplitBankLease {
    void *destination=nullptr;
    std::size_t bytes=0,descriptor_alignment=0;
    std::uint64_t memory_flags=0,allocation_owner=0;
};
}
// The callback is synchronous. Its caller must already own the CPU role and
// keep the tensor, device, descriptor and GPU epoch alive. It must not retain
// this pointer or start an operation whose completion escapes the callback.
// allocation_owner names actual VkDeviceMemory, not a logical slot or view.
extern "C" int ggml_app_vk_probe_owned_split_bank(ggml_tensor *,unsigned group,
    int (*)(const qwen_app::SplitBankLease &,void *),void *);
