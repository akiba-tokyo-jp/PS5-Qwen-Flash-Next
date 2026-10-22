// SPDX-License-Identifier: MIT
#pragma once
#include "monitor_clock.h"
#include <string>
namespace qwen_app {
struct Startup {
    std::string development_policy, model_receipt, web_assets;
    int port = 8086;
    bool native_display = true;
    bool monitor_validation = false;
    bool display_validation = false;
    bool runtime_validation = false;
    bool model_validation = false;
    bool vulkan_global_discovery = false;
    std::optional<ClockCalibration> clock_calibration;
    std::string admission_report = "/app0/qwen-runtime/gpu-admission.json";
};
// No-argument title startup reads this app's own data directory. Explicit
// config/legacy CLI arguments remain available for controlled native tests.
Startup read_startup(int argc, char ** argv);
} // namespace qwen_app
