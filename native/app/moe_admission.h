// SPDX-License-Identifier: MIT
#pragma once
#include "operator_admission.h"

namespace qwen_app {
inline constexpr unsigned moe_columns = 2560, moe_rows = 16, moe_experts = 512, moe_selected = 10;
inline constexpr std::uint64_t moe_fixture_bytes = std::uint64_t(moe_columns) * moe_rows * moe_experts * 2;
inline constexpr const char * moe_fixture_sha256 = "48ae4c3c1a34904384ad7349c2151dc551cad4ca3b3302e8ce73d1f90b4b39c8";
inline constexpr const char * moe_fixture_path = "/app0/qwen-runtime/original-moe-fixture.bf16";
inline constexpr std::array<std::int32_t, moe_selected> moe_expert_ids{{511, 0, 256, 17, 383, 1, 510, 127, 255, 42}};
struct MoeAdmission {
    bool passed = false;
    std::string backend;
    std::array<double, moe_rows * moe_selected> expected{};
    std::array<float, moe_rows * moe_selected> actual{};
    OperatorMetric metric;
    double elapsed_ms = 0;
};
// All 512 experts are represented by diagnostic rows. This is not a model load.
std::vector<std::uint16_t> load_original_moe_fixture(const std::string &);
MoeAdmission admit_original_moe(const std::vector<std::uint16_t> &, void (*stage)(const char *) = nullptr);
}
