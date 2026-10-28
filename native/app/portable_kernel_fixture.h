// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
namespace qwen_app {
nlohmann::json run_portable_kernel_fixture(void(*checkpoint)(),void(*stage)(const char*));
}
