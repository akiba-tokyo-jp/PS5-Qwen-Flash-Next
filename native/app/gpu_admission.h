// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <string>
namespace qwen_app {
struct GpuAdmission {
    bool passed = false;
    std::string backend;
    std::array<float, 16> expected{}, actual{};
    double max_absolute_error = 0, elapsed_ms = 0;
};
// Model-independent original-BF16 matrix/vector readback. An exception retains
// all resource backing for ordinary OS close; it never retries or frees it.
GpuAdmission admit_bf16_gpu();
} // namespace qwen_app
