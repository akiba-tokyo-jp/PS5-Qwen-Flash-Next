// SPDX-License-Identifier: MIT
#pragma once
#include "padded_bank.h"
#include <atomic>
namespace qwen_app {
struct PaddedCacheGeometry {
    std::size_t active_slots;
    constexpr std::size_t physical_slots() const {return active_slots+1;}
    constexpr std::size_t tensor_bytes() const {return active_slots*padded_bank_stride+bank_expert_bytes;}
    constexpr std::size_t cache_bytes() const {
        return active_slots==53?(512ull<<20):3*physical_slots()*padded_bank_stride;
    }
    PaddedBankSlot slot(std::size_t index,std::size_t residue,std::size_t allocation,
                        std::size_t alignment) const {
        if((active_slots!=53&&active_slots!=128)||index>=active_slots)
            throw std::invalid_argument("Selected padded-cache slot is outside its exact scope");
        // The original arithmetic and descriptor checks remain authoritative.
        const auto local=padded_bank_slot(0,residue,allocation,alignment);
        const auto offset=index*padded_bank_stride;
        if(offset>allocation||local.requested_bytes>allocation-offset)
            throw std::length_error("Selected padded-cache read exceeds the owned bank");
        return {offset,offset+residue,local.requested_bytes};
    }
};
// Selection is process-wide and one-way, before backend/model initialization.
// Ordinary builds and policies retain the qualified 53-slot geometry.
inline std::atomic<std::size_t> selected_padded_cache_slots{53};
inline PaddedCacheGeometry selected_padded_cache_geometry() {
    return {selected_padded_cache_slots.load(std::memory_order_relaxed)};
}
inline std::size_t selected_padded_buffer_batch_limit(std::size_t actual,bool postload) {
    // Keep resident tensors on their actual pre-load limit. Only the isolated
    // expanded-cache scope splits post-load groups at the unchanged 512 MiB
    // single-buffer cap; aggregate and per-allocation admission still apply.
    return postload&&selected_padded_cache_geometry().active_slots==128&&actual>(512ull<<20)?
        (512ull<<20):actual;
}
inline void select_experimental_padded_cache_128() {
    std::size_t expected=53;
    if(!selected_padded_cache_slots.compare_exchange_strong(expected,128))
        throw std::logic_error("Experimental padded-cache geometry can only be selected once");
}
static_assert(PaddedCacheGeometry{128}.cache_bytes()==1274462208,
    "The experimental request must contain exactly three 129-plane banks");
}
