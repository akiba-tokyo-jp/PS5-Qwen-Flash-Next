// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Register one separately pinned, read-only native shader before main.
// The original external registry, decode lease and proof remain unchanged.
void qwen_app_register_additional_shader(const void*,size_t,const unsigned char*);
uint64_t qwen_app_additional_shaders_verified(void);
uint64_t qwen_app_additional_shader_modules(void);
#ifdef __cplusplus
}
#endif
