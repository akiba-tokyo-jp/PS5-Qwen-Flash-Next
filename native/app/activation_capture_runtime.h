// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <string>
namespace qwen_app {
void prepare_activation_capture(const std::string&path,const nlohmann::json&binding);
void activation_capture_request(unsigned ordinal);
nlohmann::json finish_activation_capture();
}
