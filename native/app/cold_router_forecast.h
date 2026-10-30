// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <nlohmann/json.hpp>
struct llama_context;
struct ggml_tensor;
extern "C" void qwen_app_cold_forecast_demand(unsigned,const std::int32_t*,const std::int32_t*);
extern "C" bool qwen_app_cold_forecast_resident(unsigned,unsigned);
namespace qwen_app {
bool evaluate_cold_forecast(ggml_tensor*,bool,void*) noexcept;
void cold_forecast_begin(llama_context*,unsigned,void(*)(),void(*)());
nlohmann::json cold_forecast_finish(llama_context*);
}
