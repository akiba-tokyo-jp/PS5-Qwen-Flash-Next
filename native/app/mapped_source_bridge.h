// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
// Required only by the isolated native engine overlays. No optional host-pointer
// import or driver allocation is performed by these source-reader callbacks.
extern "C" {
bool qwen_app_model_reads_enabled();
bool qwen_app_model_compute_limits_enabled();
bool llama_app_mapped_source_hooks();
bool llama_app_bounded_expert_advice_hooks();
bool ggml_app_mapped_upload_hooks();
bool ggml_app_mapped_async_hooks();
bool ggml_app_bounded_cpu_fallback_hooks();
bool ggml_app_bounded_device_buffers_hooks();
void qwen_app_model_device_buffer_reserve(std::size_t);
void qwen_app_model_device_buffer_commit(const void *);
void qwen_app_model_device_buffer_released(const void *);
void qwen_app_model_mapping_open(void *, std::size_t, int);
void qwen_app_model_mapping_before_unmap(void *, std::size_t);
void qwen_app_model_mapping_after_unmap(void *, std::size_t);
bool qwen_app_model_source_range(const void *, std::size_t);
const void * qwen_app_model_source_chunk(const void *, std::size_t, std::size_t *);
void qwen_app_model_source_chunk_completed();
}
