// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
extern "C" void qwen_app_cold_forecast_demand(unsigned,const std::int32_t*,const std::int32_t*);
extern "C" bool qwen_app_cold_forecast_resident(unsigned,unsigned);
