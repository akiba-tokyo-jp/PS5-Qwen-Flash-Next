// SPDX-License-Identifier: MIT
#pragma once
#include "first_generation.h"
#include "mapped_source.h"
#include <cstdint>

namespace qwen_app {
// Pinned original config: (ngram_size - 1) * heads_per_ngram = 16,
// BF16 PLE rows have 160 columns; input embedding rows have 2560 columns.
// Retain the logical two-page address bound for all three requests. Protected
// virtual keys have no resident file pages. The single Direct read window and
// CPU scratch are already in the tracked heap; Vulkan context buffers retain
// their separate admission. Do not subtract the logical source span from the
// physical heap budget a second time. Native setup verifies window ownership.
// Fresh Flexible/kernel guards still apply.
inline constexpr std::uint64_t model_CPU_budget_bytes = 512ull << 20;
inline constexpr std::uint64_t maximum_model_CPU_row_pages =
    3ull * (first_prompt_tokens + first_output_tokens) * (16 + 1) * 2;
inline constexpr std::uint64_t maximum_addressed_model_CPU_bytes =
    maximum_model_CPU_row_pages * model_read_alignment;
inline constexpr std::uint64_t maximum_resident_model_CPU_source_bytes = 0;
inline constexpr std::uint64_t maximum_model_CPU_heap_bytes =
    model_CPU_budget_bytes - maximum_resident_model_CPU_source_bytes;
static_assert(160 * 2 < model_read_alignment && 2560 * 2 < model_read_alignment);
static_assert(maximum_addressed_model_CPU_bytes == 160432128);
static_assert(maximum_model_CPU_heap_bytes + maximum_resident_model_CPU_source_bytes == model_CPU_budget_bytes);
}
