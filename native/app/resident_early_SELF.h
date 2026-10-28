// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>
struct qwen_resident_early_SELF {
    uint64_t identity[10],bytes,read_calls,elapsed_ns;
    uint32_t free_before,free_after,minimum_free,minimum,reserved,selected_floor;
    unsigned char sha256[32];int completed,Direct_flag_verified;
};
#ifdef __cplusplus
extern "C" {
#endif
int qwen_resident_hash_SELF_before_CXX(void);
const struct qwen_resident_early_SELF *qwen_resident_early_SELF_result(void);
#ifdef __cplusplus
}
#endif
