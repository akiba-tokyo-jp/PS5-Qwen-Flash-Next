// SPDX-License-Identifier: MIT
#pragma once
#include "http_app.h"
#include <nlohmann/json.hpp>

namespace qwen_app {
inline constexpr const char * demo_prompt = "Count from 1 to 20, separated by commas.";
// The listener only transports requests and observations. All model operations
// execute synchronously on the caller's already admitted producer thread.
using DemoExecute = std::function<nlohmann::json(unsigned, const std::function<bool()> &,
    const std::function<void(const nlohmann::json &)> &)>;
nlohmann::json serve_bounded_demo(const std::string & run_id, const std::string & assets,
    const std::string & bind_address, int port, const HardwareInfo &, const DemoExecute &,
    const std::function<void(const MonitorSnapshot &)> &,
    const std::function<void(const nlohmann::json &)> & ready);
}
