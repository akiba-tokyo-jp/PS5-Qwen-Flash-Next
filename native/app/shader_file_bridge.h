// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
struct qwen_shader_file_plan {
    uint64_t bytes;
    size_t input_window_bytes;
    unsigned char sha256[32];
};
// Registration describes immutable original resources. It opens no file,
// allocates no buffer and never initializes Vulkan.
void qwen_app_register_shader_file_plan(const struct qwen_shader_file_plan *);
#ifdef __cplusplus
}
#endif
