/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
struct qwen_early_CPU_tables {
    uint64_t begin,end,mapped_bytes,allocated_bytes,available_before;
    int64_t physical;
    uint32_t free_before,free_after,minimum_free;
    int status,allocated,mapped,zeroed,checksum_passed,all_CPU_operations_returned;
    uint64_t checksum;
};
#ifdef __cplusplus
extern "C" {
#endif
const struct qwen_early_CPU_tables*qwen_early_CPU_tables_result(void);
#ifdef __cplusplus
}
#endif
