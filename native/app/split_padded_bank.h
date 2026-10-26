// SPDX-License-Identifier: MIT
#pragma once
#include "padded_bank.h"
#include <array>
namespace qwen_app {
// Unqualified layout prototype: two independent backing groups, each with
// three role views. Roles within a group may share one actual buffer owner.
// Byte-storage roots are required; current 3D ownership/dispatch guards reject
// this layout and must not be relaxed by this arithmetic description.
inline constexpr std::array<std::size_t,2> split_bank_active{{26,27}};
inline constexpr std::array<std::size_t,2> split_bank_planes{{27,27}};
inline constexpr std::size_t split_bank_total_bytes=3*(split_bank_planes[0]+split_bank_planes[1])*padded_bank_stride;
static_assert(split_bank_active[0]+split_bank_active[1]==padded_bank_active_slots);
static_assert(split_bank_total_bytes==3*padded_bank_physical_slots*padded_bank_stride);
static_assert(split_bank_total_bytes<=(512u<<20));
struct SplitPaddedSlot {
    std::size_t group=0,local_slot=0,role_allocation_bytes=0;
    PaddedBankSlot envelope;
};
inline SplitPaddedSlot split_padded_slot(std::size_t global_slot,std::size_t residue,std::size_t alignment) {
    if(global_slot>=padded_bank_active_slots)throw std::invalid_argument("Split global cache slot exceeds the original 53 slots");
    const auto group=std::size_t(global_slot>=split_bank_active[0]);
    const auto local=group?global_slot-split_bank_active[0]:global_slot;
    const auto bytes=split_bank_planes[group]*padded_bank_stride;
    if(local>=split_bank_active[group])throw std::invalid_argument("Split local slot is outside its group");
    return {group,local,bytes,padded_bank_slot(local,residue,bytes,alignment)};
}
}
