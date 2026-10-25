// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
namespace qwen_app {
inline constexpr std::size_t bank_read_alignment=16384,bank_expert_bytes=3276800;
inline constexpr std::size_t padded_bank_stride=3293184,padded_bank_active_slots=53,padded_bank_physical_slots=54;
inline constexpr std::size_t padded_bank_tensor_bytes=(padded_bank_physical_slots-1)*padded_bank_stride+bank_expert_bytes;
static_assert(3*padded_bank_physical_slots*padded_bank_stride<=(512u<<20),"Padded banks must fit the existing cache cap");
struct PaddedBankSlot {
    std::size_t aligned_write_offset=0,payload_offset=0,requested_bytes=0;
};
inline PaddedBankSlot padded_bank_slot(std::size_t slot,std::size_t residue,
    std::size_t allocation_bytes,std::size_t descriptor_alignment) {
    if(slot>=padded_bank_active_slots||residue>=bank_read_alignment||!descriptor_alignment||
       descriptor_alignment&(descriptor_alignment-1)||residue%descriptor_alignment)
        throw std::invalid_argument("Padded bank slot or real descriptor alignment refused");
    const auto start=slot*padded_bank_stride;
    const auto request=(residue+bank_expert_bytes+bank_read_alignment-1)&~(bank_read_alignment-1);
    if(start>allocation_bytes||request>allocation_bytes-start||request>padded_bank_stride)
        throw std::length_error("Padded read envelope exceeds its actual owned allocation");
    return {start,start+residue,request};
}
// False is an eligibility result before any I/O. A crossing or EOF envelope
// keeps the already-qualified staged split/EOF reader; it is not retried here.
inline bool padded_source_envelope(std::uint64_t offset,std::uint64_t physical_bytes,
    std::uint64_t &aligned,std::size_t &requested) {
    const auto residue=std::size_t(offset%bank_read_alignment);
    if(offset>physical_bytes||bank_expert_bytes>physical_bytes-offset)return false;
    aligned=offset-residue;
    requested=(residue+bank_expert_bytes+bank_read_alignment-1)&~(bank_read_alignment-1);
    return requested<=physical_bytes-aligned;
}
}
