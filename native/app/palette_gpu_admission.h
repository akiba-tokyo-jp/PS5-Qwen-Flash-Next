// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include "palette_gpu_policy.h"
namespace qwen_app {
nlohmann::json admit_palette_gpu(const nlohmann::json &,const std::string &journal);
}
