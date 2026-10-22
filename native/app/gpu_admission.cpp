// SPDX-License-Identifier: MIT
#include "gpu_admission.h"
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <stdexcept>

namespace qwen_app {
GpuAdmission admit_bf16_gpu(void (*stage)(const char *)) {
    GpuAdmission report;
    const auto start = std::chrono::steady_clock::now();
    if (stage) stage("BF16_before_backend_init");
    auto * backend = ggml_backend_vk_init(0);
    if (!backend) throw std::runtime_error("Vulkan admission backend is unavailable");
    if (stage) stage("BF16_backend_init_completed");
    report.backend = ggml_backend_name(backend);
    ggml_init_params params{};
    params.mem_size = ggml_tensor_overhead() * 8 + ggml_graph_overhead_custom(32, false);
    params.no_alloc = true;
    auto * context = ggml_init(params);
    if (!context) throw std::runtime_error("BF16 admission context allocation failed");
    auto * weights = ggml_new_tensor_2d(context, GGML_TYPE_BF16, 32, 16);
    auto * input = ggml_new_tensor_2d(context, GGML_TYPE_F32, 32, 1);
    auto * output = ggml_mul_mat(context, weights, input);
    ggml_set_input(weights); ggml_set_input(input); ggml_set_output(output);
    auto * graph = ggml_new_graph_custom(context, 32, false);
    ggml_build_forward_expand(graph, output);
    if (!ggml_backend_dev_supports_op(ggml_backend_get_device(backend), output))
        throw std::runtime_error("Original-BF16 admission operation is unsupported");
    if (stage) stage("BF16_operation_supported_before_allocation");
    auto * buffer = ggml_backend_alloc_ctx_tensors(context, backend);
    if (!buffer) throw std::runtime_error("BF16 admission device allocation failed");
    if (stage) stage("BF16_allocation_completed");
    std::array<ggml_bf16_t, 32 * 16> matrix{};
    std::array<float, 32> vector{};
    for (unsigned k = 0; k < 32; ++k) vector[k] = float(int(k % 7) - 3) * 0.5f;
    for (unsigned row = 0; row < 16; ++row) for (unsigned k = 0; k < 32; ++k) {
        const float value = float(int((row * 3 + k) % 17) - 8) * 0.25f;
        matrix[row * 32 + k] = ggml_fp32_to_bf16(value);
        report.expected[row] += value * vector[k];
    }
    ggml_backend_tensor_set(weights, matrix.data(), 0, sizeof(matrix));
    ggml_backend_tensor_set(input, vector.data(), 0, sizeof(vector));
    if (stage) stage("BF16_upload_completed_before_graph_compute");
    if (ggml_backend_graph_compute(backend, graph) != GGML_STATUS_SUCCESS)
        throw std::runtime_error("BF16 admission compute failed; resources retained");
    if (stage) stage("BF16_graph_compute_returned_success");
    ggml_backend_synchronize(backend);
    if (stage) stage("BF16_synchronize_returned_before_readback");
    ggml_backend_tensor_get(output, report.actual.data(), 0, sizeof(report.actual));
    if (stage) stage("BF16_readback_completed");
    report.passed = true;
    for (unsigned i = 0; i < report.actual.size(); ++i) {
        const double error = std::abs(double(report.actual[i]) - report.expected[i]);
        report.max_absolute_error = std::max(report.max_absolute_error, error);
        if (!std::isfinite(report.actual[i]) || error > 1e-5 + 1e-5 * std::abs(report.expected[i])) report.passed = false;
    }
    report.elapsed_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    if (report.passed) {
        if (stage) stage("BF16_numerical_gate_passed_before_release");
        ggml_backend_buffer_free(buffer); ggml_free(context); ggml_backend_free(backend);
        if (stage) stage("BF16_successful_resource_release_completed");
    } else if (stage) stage("BF16_numerical_gate_failed_backing_retained");
    // A completed but numerically failed case also keeps backing for inspection.
    return report;
}
} // namespace qwen_app
