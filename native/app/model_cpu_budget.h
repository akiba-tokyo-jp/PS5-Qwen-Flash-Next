// SPDX-License-Identifier: MIT
#pragma once
#include "first_generation.h"
#include "mapped_source.h"
#include <cstdint>

namespace qwen_app {
// Pinned original config: (ngram_size - 1) * heads_per_ngram = 16,
// BF16 PLE rows have 160 columns; input embedding rows have 2560 columns.
// Each row can straddle two native 16 KiB pages. Count every addressed page
// across all three requests even when repeated rows share a physical page.
// Kernel readahead is not bounded by this calculation; fresh OS reserve checks
// remain mandatory. GPU weight/expert uploads use the separate direct window.
inline constexpr std::uint64_t model_CPU_budget_bytes = 512ull << 20;
inline constexpr std::uint64_t maximum_model_CPU_row_pages =
    3ull * (first_prompt_tokens + first_output_tokens) * (16 + 1) * 2;
inline constexpr std::uint64_t maximum_addressed_model_CPU_bytes =
    maximum_model_CPU_row_pages * model_read_alignment;
inline constexpr std::uint64_t maximum_model_CPU_heap_bytes =
    model_CPU_budget_bytes - maximum_addressed_model_CPU_bytes;
static_assert(160 * 2 < model_read_alignment && 2560 * 2 < model_read_alignment);
static_assert(maximum_addressed_model_CPU_bytes == 160432128);
}
