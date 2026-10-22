// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace qwen_app {
inline constexpr unsigned operator_columns = 2560, operator_rows = 16;
inline constexpr const char * original_weight_fixture_sha256 = "08cc107ea6e34f0eb31c8cbb0d0e586b9a8ddfc1af4a9226c027dbf221cc2154";
struct OperatorMetric {
    unsigned values = 0;
    bool finite = true, passed = true;
    double max_absolute_error = 0, normalized_rmse = 0;
};
struct OperatorAdmission {
    bool passed = false;
    std::string backend;
    std::array<double, operator_rows> expected{};
    std::array<float, operator_rows> actual{};
    std::vector<float> norm_actual, silu_actual;
    OperatorMetric matvec, rms_norm, silu;
    double elapsed_ms = 0;
};
// The loader hashes the exact small diagnostic file before GPU initialization.
// It never loads or evaluates the complete learned model.
std::vector<std::uint16_t> load_original_weight_fixture(const std::string &, const std::string &);
OperatorAdmission admit_original_weight_operations(const std::vector<std::uint16_t> &,
                                                   void (*stage)(const char *) = nullptr);
}
