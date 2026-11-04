// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <nlohmann/json.hpp>
namespace qwen_app {
void prepare_model_relative_prefetch(bool,bool(*)(std::size_t),std::uint64_t,std::uint64_t);
void begin_model_relative_prefetch_request();
nlohmann::json finish_model_relative_prefetch_request();
nlohmann::json retire_model_relative_prefetch_after_original_owners();
}
