// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <limits>
#include <numeric>
#include <stdexcept>

namespace qwen_app {
struct ExpertQ2KGeometry {
    static constexpr std::size_t block_values=256,block_bytes=84,read_alignment=16384;
    std::size_t columns,rows;
    std::size_t payload_bytes() const {
        if(columns!=2560||rows!=640||columns%block_values)
            throw std::invalid_argument("Q2_K admits only original Gate/Up rows divisible by 256");
        return columns/block_values*block_bytes*rows;
    }
    static std::size_t rounded(std::size_t bytes,std::size_t alignment){
        if(!alignment||(alignment&(alignment-1))||bytes>std::numeric_limits<std::size_t>::max()-(alignment-1))
            throw std::invalid_argument("Quantized cache alignment or size overflow");
        return (bytes+alignment-1)&~(alignment-1);
    }
    std::size_t contiguous_bank_bytes(std::size_t active,std::size_t alignment) const {
        if(active<10||active>48*512||active+1>std::numeric_limits<std::size_t>::max()/payload_bytes())
            throw std::invalid_argument("Quantized cache cannot omit selected Experts or overflow");
        return rounded((active+1)*payload_bytes(),alignment);
    }
    std::size_t maximum_contiguous_slots(std::size_t budget,std::size_t alignment) const {
        std::size_t slots=0;
        for(std::size_t n=10;n<=48*512;++n){
            const auto bank=contiguous_bank_bytes(n,alignment);
            if(bank>(512ull<<20)||bank>budget/3)break;
            slots=n;
        }
        return slots;
    }
    // Optional Direct-bank layouts must satisfy both quantization-block and
    // read alignment. Rounding only to 16 KiB truncates nb[2]/18 in Vulkan.
    std::size_t padded_stride() const {
        const auto quantum=std::lcm(read_alignment,block_bytes);
        const auto envelope=payload_bytes()+read_alignment-1;
        return (envelope+quantum-1)/quantum*quantum;
    }
};
}
