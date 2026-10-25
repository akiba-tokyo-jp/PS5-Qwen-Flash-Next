// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
// The descriptor still identifies the exact first physical part. Only the
// GGUF engine's address-key size uses the original complete logical length.
extern "C" std::size_t qwen_app_model_source_logical_size(int fd, std::size_t physical_bytes);
