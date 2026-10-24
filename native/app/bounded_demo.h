// SPDX-License-Identifier: MIT
#pragma once
#include "http_app.h"
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <vector>

namespace qwen_app {
inline constexpr const char * demo_prompt = "Count from 1 to 8, separated by commas. Reply with only the sequence.";
inline void require_demo_sequence(const std::vector<unsigned char> & bytes) {
    std::string compact;
    for (const auto byte : bytes)
        if (byte != ' ' && byte != '\t' && byte != '\r' && byte != '\n') compact += static_cast<char>(byte);
    if (compact != "1,2,3,4,5,6,7,8")
        throw std::runtime_error("The completed external response differs from its bounded counting sequence");
}
// The listener only transports requests and observations. All model operations
// execute synchronously on the caller's already admitted producer thread.
using DemoExecute = std::function<nlohmann::json(unsigned, const std::function<bool()> &,
    const std::function<void(const nlohmann::json &)> &)>;
nlohmann::json serve_bounded_demo(const std::string & run_id, const std::string & assets,
    const std::string & bind_address, int port, const HardwareInfo &, const DemoExecute &,
    const std::function<void(const MonitorSnapshot &)> &,
    const std::function<void(const nlohmann::json &)> & ready);
}
