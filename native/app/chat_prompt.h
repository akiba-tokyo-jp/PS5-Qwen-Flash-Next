// SPDX-License-Identifier: MIT
#pragma once
#include "jinja/parser.h"
#include "nlohmann/json.hpp"
#include <string>
namespace qwen_app {
std::string render_chat_prompt(const std::string & source, const jinja::program & program,
    const nlohmann::json & messages, bool thinking);
std::string render_first_generation_prompt(const std::string & original_template);
std::string render_bounded_user_prompt(const std::string & original_template, const std::string & prompt);
}
