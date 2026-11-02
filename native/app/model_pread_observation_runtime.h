// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <string>
namespace qwen_app {
void begin_model_pread_observation();
void stop_model_pread_observation_after_request_completion();
nlohmann::json export_model_pread_observation_after_owner_retirement(const std::string&,const nlohmann::json&);
}
