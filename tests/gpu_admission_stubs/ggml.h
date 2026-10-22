// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
struct ggml_context {};
struct ggml_cgraph {};
enum ggml_type { GGML_TYPE_F32, GGML_TYPE_BF16 };
enum ggml_status { GGML_STATUS_SUCCESS, GGML_STATUS_FAILED };
struct ggml_bf16_t { std::uint16_t bits; };
struct ggml_tensor { ggml_type type; std::int64_t width, height; int tag; };
struct ggml_init_params { std::size_t mem_size; void * mem_buffer; bool no_alloc; };
using ggml_backend_t = void *;
using ggml_backend_buffer_t = void *;
extern "C" {
std::size_t ggml_tensor_overhead();
std::size_t ggml_graph_overhead_custom(std::size_t, bool);
ggml_context * ggml_init(ggml_init_params);
ggml_tensor * ggml_new_tensor_2d(ggml_context *, ggml_type, std::int64_t, std::int64_t);
ggml_tensor * ggml_mul_mat(ggml_context *, ggml_tensor *, ggml_tensor *);
void ggml_set_input(ggml_tensor *);
void ggml_set_output(ggml_tensor *);
ggml_cgraph * ggml_new_graph_custom(ggml_context *, std::size_t, bool);
void ggml_build_forward_expand(ggml_cgraph *, ggml_tensor *);
ggml_bf16_t ggml_fp32_to_bf16(float);
ggml_backend_t ggml_backend_vk_init(std::size_t);
const char * ggml_backend_name(ggml_backend_t);
void * ggml_backend_get_device(ggml_backend_t);
bool ggml_backend_dev_supports_op(void *, const ggml_tensor *);
ggml_backend_buffer_t ggml_backend_alloc_ctx_tensors(ggml_context *, ggml_backend_t);
void ggml_backend_tensor_set(ggml_tensor *, const void *, std::size_t, std::size_t);
ggml_status ggml_backend_graph_compute(ggml_backend_t, ggml_cgraph *);
void ggml_backend_synchronize(ggml_backend_t);
void ggml_backend_tensor_get(const ggml_tensor *, void *, std::size_t, std::size_t);
void ggml_backend_buffer_free(ggml_backend_buffer_t);
void ggml_free(ggml_context *);
void ggml_backend_free(ggml_backend_t);
}
