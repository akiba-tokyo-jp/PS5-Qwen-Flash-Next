// SPDX-License-Identifier: MIT
#include "moe_admission.h"
#include "model_integrity.h"
#include "ggml.h"
#include "ggml-alloc.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <stdexcept>

namespace qwen_app {
std::vector<std::uint16_t> load_original_moe_fixture(const std::string & path) {
    verify_model_file(path, moe_fixture_bytes, moe_fixture_sha256, {}, 30);
    std::ifstream file(path, std::ios::binary);
    std::vector<std::uint16_t> bits(moe_fixture_bytes / 2);
    if (!file.read(reinterpret_cast<char *>(bits.data()), moe_fixture_bytes) || file.peek() != std::char_traits<char>::eof())
        throw std::runtime_error("Original MoE fixture size changed after verification");
    for (auto word : bits)
        if ((word & 0x7f80u) == 0x7f80u) throw std::runtime_error("Nonfinite original MoE fixture is not admitted");
    return bits;
}

MoeAdmission admit_original_moe(const std::vector<std::uint16_t> & bits, void (*stage)(const char *)) {
    if (bits.size() != moe_fixture_bytes / 2)
        throw std::invalid_argument("The exact all-expert BF16 diagnostic is required");
    for (auto word : bits)
        if ((word & 0x7f80u) == 0x7f80u) throw std::invalid_argument("Nonfinite MoE input is not admitted");
    MoeAdmission report;
    const auto started = std::chrono::steady_clock::now();
    std::array<float, moe_columns> input{};
    for (unsigned k = 0; k < moe_columns; ++k) input[k] = float(int(k % 7) - 3) * 0.5f;
    for (unsigned slot = 0; slot < moe_selected; ++slot) {
        const auto expert = moe_expert_ids[slot];
        if (expert < 0 || expert >= std::int32_t(moe_experts)) throw std::logic_error("Invalid diagnostic expert ID");
        for (unsigned row = 0; row < moe_rows; ++row) for (unsigned k = 0; k < moe_columns; ++k) {
            const auto word = bits[(std::size_t(expert) * moe_rows + row) * moe_columns + k];
            ggml_bf16_t value;
            static_assert(sizeof(value) == 2, "Original BF16 must remain 16 bits");
            std::memcpy(&value, &word, 2);
            report.expected[slot * moe_rows + row] += double(ggml_bf16_to_fp32(value)) * input[k];
        }
    }
    if (stage) stage("MoE_CPU_double_references_completed_before_compute_backend");
    auto * backend = ggml_backend_vk_init(0);
    if (!backend) throw std::runtime_error("Vulkan MoE admission backend is unavailable");
    report.backend = ggml_backend_name(backend);
    ggml_init_params params{};
    params.mem_size = ggml_tensor_overhead() * 8 + ggml_graph_overhead_custom(16, false);
    params.no_alloc = true;
    auto * context = ggml_init(params);
    if (!context) throw std::runtime_error("MoE admission CPU metadata allocation failed");
    auto * weights = ggml_new_tensor_3d(context, GGML_TYPE_BF16, moe_columns, moe_rows, moe_experts);
    auto * vector = ggml_new_tensor_3d(context, GGML_TYPE_F32, moe_columns, 1, 1);
    auto * ids = ggml_new_tensor_2d(context, GGML_TYPE_I32, moe_selected, 1);
    auto * output = ggml_mul_mat_id(context, weights, vector, ids);
    ggml_set_input(weights); ggml_set_input(vector); ggml_set_input(ids); ggml_set_output(output);
    auto * graph = ggml_new_graph_custom(context, 16, false);
    ggml_build_forward_expand(graph, output);
    if (!ggml_backend_dev_supports_op(ggml_backend_get_device(backend), output))
        throw std::runtime_error("Original BF16 MUL_MAT_ID is unsupported before allocation");
    if (stage) stage("MoE_indexed_operation_supported_before_device_allocation");
    auto * buffer = ggml_backend_alloc_ctx_tensors(context, backend);
    if (!buffer) throw std::runtime_error("MoE admission device allocation failed");
    constexpr std::size_t upload_chunk = 8u << 20;
    const auto * bytes = reinterpret_cast<const unsigned char *>(bits.data());
    for (std::size_t offset = 0; offset < moe_fixture_bytes; offset += upload_chunk)
        ggml_backend_tensor_set(weights, bytes + offset, offset, std::min<std::size_t>(upload_chunk, moe_fixture_bytes - offset));
    ggml_backend_tensor_set(vector, input.data(), 0, sizeof(input));
    ggml_backend_tensor_set(ids, moe_expert_ids.data(), 0, sizeof(moe_expert_ids));
    if (stage) stage("MoE_all512_experts_and_top10_IDs_uploaded_before_single_graph_compute");
    if (ggml_backend_graph_compute(backend, graph) != GGML_STATUS_SUCCESS)
        throw std::runtime_error("MoE admission compute failed; backing retained");
    ggml_backend_synchronize(backend);
    if (stage) stage("MoE_synchronized_before_readback");
    ggml_backend_tensor_get(output, report.actual.data(), 0, sizeof(report.actual));
    report.metric.values = report.actual.size();
    double error_squares = 0, reference_squares = 0;
    for (unsigned i = 0; i < report.actual.size(); ++i) {
        const auto error = std::abs(double(report.actual[i]) - report.expected[i]);
        report.metric.finite = report.metric.finite && std::isfinite(report.actual[i]) && std::isfinite(report.expected[i]);
        if (!std::isfinite(error) || error > 1e-5 + 1e-5 * std::abs(report.expected[i])) report.metric.passed = false;
        if (std::isfinite(error)) report.metric.max_absolute_error = std::max(report.metric.max_absolute_error, error);
        error_squares += error * error; reference_squares += report.expected[i] * report.expected[i];
    }
    report.metric.normalized_rmse = reference_squares > 0 ? std::sqrt(error_squares / reference_squares)
        : error_squares == 0 ? 0 : INFINITY;
    report.passed = report.metric.passed = report.metric.passed && report.metric.finite &&
        std::isfinite(report.metric.normalized_rmse) && report.metric.normalized_rmse <= 0.01;
    report.elapsed_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
    if (report.passed) {
        if (stage) stage("MoE_all_numerical_gates_passed_before_release");
        ggml_backend_buffer_free(buffer); ggml_free(context); ggml_backend_free(backend);
        if (stage) stage("MoE_completed_resources_deferred_for_positive_retirement");
    } else if (stage) stage("MoE_numerical_failure_backing_retained");
    return report;
}
}
