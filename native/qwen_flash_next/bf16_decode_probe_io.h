// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
int bf16_probe_start(void);
int bf16_probe_decode(const unsigned char *,size_t,unsigned char *,size_t,unsigned char *,size_t);
int bf16_probe_stop(void);
#ifdef __cplusplus
}
#endif
