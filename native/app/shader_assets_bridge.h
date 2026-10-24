// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct qwen_shader_asset {
    const char *name;
    const unsigned char *storage;
    size_t storage_bytes;
    size_t original_bytes;
    unsigned char original_sha256[32];
};
struct qwen_shader_lookup {
    const void *const *observed_data;
    const uint64_t *observed_size;
    const void *expected_data;
    uint64_t expected_size;
};
// Generated immutable resources register pointers only, before main. Decoding
// requires separate post-integrity CPU admission and never starts Vulkan.
void qwen_app_register_shader_assets(const struct qwen_shader_asset *,size_t);
void qwen_app_register_shader_lookups(const struct qwen_shader_lookup *,size_t);
const void *qwen_app_prepare_shader_code(const void *,size_t,size_t *,void **);
// Call only after CPU-only byte verification or positive CreateShaderModule.
// The selected Mesa module provider copies pCode before returning success.
void qwen_app_complete_shader_code(void *);
#ifdef __cplusplus
}
#endif
