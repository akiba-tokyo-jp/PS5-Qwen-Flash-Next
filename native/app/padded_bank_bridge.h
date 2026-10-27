// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
struct ggml_tensor;
extern "C" {
bool qwen_app_padded_index_layout(const ggml_tensor *);
std::size_t qwen_app_padded_buffer_batch_limit(std::size_t);
int ggml_app_vk_probe_owned_bank(ggml_tensor *,
    int (*)(void *,std::size_t,std::uint64_t,std::size_t,void *),void *);
}
