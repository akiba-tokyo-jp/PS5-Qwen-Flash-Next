// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
struct ggml_tensor;
struct qwen_predictive_cache_stats {
    std::uint64_t proposals=0,loads=0,useful=0,unused=0,ineligible=0;
    std::uint64_t logical_bytes=0,foreground_wait_ns=0,worker_read_ns=0;
};
extern "C" {
bool qwen_app_predictive_cache_enabled();
void qwen_app_configure_predictive_cache(bool);
void qwen_app_predictive_cache_counters(qwen_predictive_cache_stats *);
bool qwen_app_begin_predictive_expert(ggml_tensor *const *,const void *const *,int,const std::size_t *);
void qwen_app_complete_predictive_expert();
}
