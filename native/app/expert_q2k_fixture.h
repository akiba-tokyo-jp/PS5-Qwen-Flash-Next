// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
namespace qwen_app {
nlohmann::json run_expert_q2k_fixture(void(*checkpoint)(),void(*stage)(const char*));
}
