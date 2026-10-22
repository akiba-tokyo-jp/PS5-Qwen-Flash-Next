// SPDX-License-Identifier: MIT
#include "operator_admission.h"
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
std::vector<std::uint16_t> load_original_weight_fixture(const std::string & path, const std::string & digest) {
    constexpr auto elements = operator_columns * operator_rows;
    verify_model_file(path, elements * 2, digest, {}, 30);
    std::ifstream file(path, std::ios::binary);
    std::vector<std::uint16_t> bits(elements);
    if (!file.read(reinterpret_cast<char *>(bits.data()), bits.size() * 2) || file.peek() != std::char_traits<char>::eof())
        throw std::runtime_error("Original BF16 operation fixture size changed after verification");
    for (auto value : bits)
        if ((value & 0x7f80u) == 0x7f80u) throw std::runtime_error("Nonfinite original BF16 operation fixture is not admitted");
    return bits;
}

OperatorAdmission admit_original_weight_operations(const std::vector<std::uint16_t> & bits,
                                                    void (*stage)(const char *)) {
    if (bits.size() != operator_columns * operator_rows)
        throw std::invalid_argument("The exact bounded original BF16 matrix is required");
    for (auto value : bits)
        if ((value & 0x7f80u) == 0x7f80u) throw std::invalid_argument("Nonfinite BF16 input is not admitted");
    OperatorAdmission report;
    const auto started = std::chrono::steady_clock::now();
    std::vector<float> input(operator_columns);
    report.norm_actual.resize(operator_columns); report.silu_actual.resize(operator_columns);
    std::vector<double> norm_expected(operator_columns), silu_expected(operator_columns);
    double squares = 0;
    for (unsigned k = 0; k < operator_columns; ++k) {
        input[k] = float(int(k % 7) - 3) * 0.5f;
        squares += double(input[k]) * input[k];
    }
    const auto inverse_rms = 1.0 / std::sqrt(squares / operator_columns + 1e-6);
    for (unsigned k = 0; k < operator_columns; ++k) {
        norm_expected[k] = double(input[k]) * inverse_rms;
        silu_expected[k] = norm_expected[k] / (1.0 + std::exp(-norm_expected[k]));
    }
    for (unsigned row = 0; row < operator_rows; ++row) for (unsigned k = 0; k < operator_columns; ++k) {
        ggml_bf16_t value;
        static_assert(sizeof(value) == 2, "Original BF16 storage must remain 16 bits");
        const auto word = bits[row * operator_columns + k]; std::memcpy(&value, &word, 2);
        report.expected[row] += double(ggml_bf16_to_fp32(value)) * input[k];
    }
    if (stage) stage("operators_CPU_double_references_completed_before_compute_backend");
    auto * backend = ggml_backend_vk_init(0);
    if (!backend) throw std::runtime_error("Vulkan operation admission backend is unavailable");
    report.backend = ggml_backend_name(backend);
    ggml_init_params params{};
    params.mem_size = ggml_tensor_overhead() * 10 + ggml_graph_overhead_custom(32, false);
    params.no_alloc = true;
    auto * context = ggml_init(params);
    if (!context) throw std::runtime_error("Operation admission CPU metadata allocation failed");
    auto * weights = ggml_new_tensor_2d(context, GGML_TYPE_BF16, operator_columns, operator_rows);
    auto * vector = ggml_new_tensor_2d(context, GGML_TYPE_F32, operator_columns, 1);
    auto * matvec = ggml_mul_mat(context, weights, vector);
    auto * norm = ggml_rms_norm(context, vector, 1e-6f);
    auto * silu = ggml_silu(context, norm);
    ggml_set_input(weights); ggml_set_input(vector);
    auto * graph = ggml_new_graph_custom(context, 32, false);
    for (auto * output : {matvec, norm, silu}) {
        if (!ggml_backend_dev_supports_op(ggml_backend_get_device(backend), output))
            throw std::runtime_error("A required original-weight operation is unsupported before allocation");
        ggml_set_output(output); ggml_build_forward_expand(graph, output);
    }
    if (stage) stage("operators_all_supported_before_device_allocation");
    auto * buffer = ggml_backend_alloc_ctx_tensors(context, backend);
    if (!buffer) throw std::runtime_error("Operation admission device allocation failed");
    ggml_backend_tensor_set(weights, bits.data(), 0, bits.size() * 2);
    ggml_backend_tensor_set(vector, input.data(), 0, input.size() * sizeof(float));
    if (stage) stage("operators_uploaded_before_single_graph_compute");
    if (ggml_backend_graph_compute(backend, graph) != GGML_STATUS_SUCCESS)
        throw std::runtime_error("Operation admission compute failed; backing retained");
    ggml_backend_synchronize(backend);
    if (stage) stage("operators_synchronized_before_readbacks");
    ggml_backend_tensor_get(matvec, report.actual.data(), 0, sizeof(report.actual));
    ggml_backend_tensor_get(norm, report.norm_actual.data(), 0, report.norm_actual.size() * sizeof(float));
    ggml_backend_tensor_get(silu, report.silu_actual.data(), 0, report.silu_actual.size() * sizeof(float));
    auto metric = [](const auto & expected, const auto & actual) {
        OperatorMetric result; result.values = actual.size(); double error_squares = 0, reference_squares = 0;
        for (unsigned i = 0; i < actual.size(); ++i) {
            const auto error = std::abs(double(actual[i]) - expected[i]);
            result.finite = result.finite && std::isfinite(actual[i]) && std::isfinite(expected[i]);
            if (!std::isfinite(error) || error > 1e-5 + 1e-5 * std::abs(expected[i])) result.passed = false;
            if (std::isfinite(error)) result.max_absolute_error = std::max(result.max_absolute_error, error);
            error_squares += error * error; reference_squares += expected[i] * expected[i];
        }
        result.normalized_rmse = reference_squares > 0 ? std::sqrt(error_squares / reference_squares)
            : error_squares == 0 ? 0 : INFINITY;
        result.passed = result.passed && result.finite && std::isfinite(result.normalized_rmse) && result.normalized_rmse <= 0.01;
        return result;
    };
    report.matvec = metric(report.expected, report.actual);
    report.rms_norm = metric(norm_expected, report.norm_actual); report.silu = metric(silu_expected, report.silu_actual);
    report.passed = report.matvec.passed && report.rms_norm.passed && report.silu.passed;
    report.elapsed_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - started).count();
    if (report.passed) {
        if (stage) stage("operators_all_numerical_gates_passed_before_release");
        ggml_backend_buffer_free(buffer); ggml_free(context); ggml_backend_free(backend);
        if (stage) stage("operators_completed_resources_deferred_for_positive_retirement");
    } else if (stage) stage("operators_numerical_failure_backing_retained");
    return report;
}
}
