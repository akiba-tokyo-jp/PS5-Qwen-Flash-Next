// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
namespace qwen_app {
nlohmann::json run_calibrated_iq2_fixture(void(*checkpoint)(),void(*stage)(const char*));
}
