// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
struct ggml_tensor;
struct qwen_six_bank_refill_stats {std::uint64_t batches=0,reads=0,logical_bytes=0;};
extern "C" {
bool qwen_app_six_bank_refill_enabled();
void qwen_app_six_bank_refill_counters(qwen_six_bank_refill_stats *);
bool qwen_app_try_six_bank_refill(ggml_tensor *const *,const void *const *,const int *,const std::size_t *);
}
namespace qwen_app {void configure_native_six_bank_refill(bool);}
