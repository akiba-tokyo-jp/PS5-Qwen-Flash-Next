// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>
namespace qwen_app {
inline constexpr std::array<std::size_t,30> original_bank_residues{{32,160,256,640,832,1120,1152,1184,
    1632,1696,1728,1760,1792,1824,2080,2208,2240,2304,2336,2784,3232,6688,6720,8320,
    11360,11424,12768,12832,12864,12928}};
struct PaddedLayoutCase {
    unsigned columns=0,rows=0,input_vectors=0;std::size_t residue=0;
    double maximum_absolute_error=0;std::uint64_t non_BF16_exact_F32_inputs=0;
    bool matrix_passed=false,vector_passed=false,non_dyadic_vector_passed=false,padding_intact=false;
};
struct PaddedLayoutResult {
    bool eligible=false,all_IO_closed=false,positive_retirement=false;
    unsigned Direct_reads=0,GPU_graphs=0;std::size_t descriptor_alignment=0;
    std::uint64_t memory_flags=0;std::vector<PaddedLayoutCase> cases;
};
void configure_padded_index_layout(bool,std::size_t descriptor_alignment=0);
PaddedLayoutResult admit_padded_bank_layout(const std::string &,const std::string &,
    void (*checkpoint)(),void (*stage)(const char *));
}
