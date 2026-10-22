// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
#include <stdbool.h>
#ifdef __cplusplus
extern "C" {
#endif
// Preserved native compatibility ABI. Qwen owns no extra import-only pool;
// ordinary Direct BO allocation remains the native winsys's responsibility.
struct ps5_ai_flex_stats {
    uint64_t reserved_bytes,used_bytes,peak_used_bytes,free_bytes;
    uint64_t allocations,active_imports,denied_allocations;
    int mapping_owned,gpu_access_granted,fault_retained,log_healthy;
};
uint64_t ps5_ai_flex_pool_bytes(void);
void ps5_ai_flex_snapshot(struct ps5_ai_flex_stats *);
bool ps5_ai_flex_grant_gpu(void *,uint64_t);
#ifdef __cplusplus
}
#endif
