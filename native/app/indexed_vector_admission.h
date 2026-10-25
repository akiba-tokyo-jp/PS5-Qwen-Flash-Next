// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>

namespace qwen_app {
inline float indexed_fixture_input(std::uint32_t column,std::uint32_t vector,bool non_dyadic) {
    return float(int((column*11+vector)%13)-6)/(non_dyadic?63.0f:64.0f);
}
struct IndexedVectorCase {
    std::uint32_t columns=0,rows=0,input_vectors=0;
    std::uint32_t non_dyadic_F32_inputs=0;
    std::array<double,2> first_ms{},warm_ms{};
    double max_absolute_error=0;
    bool passed=false;
};
// Four layouts, two timed strategies, three graphs per strategy on the same
// dyadic inputs. Each layout adds one untimed vector graph with F32 inputs
// that change when rounded to BF16, against their own F64 accumulation reference.
// At most one 32,768,000-byte BF16 bank and its matching device copy are live.
std::array<IndexedVectorCase,4> admit_indexed_vectors(void (*checkpoint)(),void (*stage)(const char *));
}
