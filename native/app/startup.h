// SPDX-License-Identifier: MIT
#pragma once
#include <string>
namespace qwen_app {
struct Startup {
    std::string development_policy, model_receipt, web_assets;
    int port = 8086;
    bool native_display = true;
    bool monitor_validation = false;
    bool display_validation = false;
    std::string admission_report = "/data/ai/qwen-flash-next/gpu-admission.json";
};
// No-argument title startup reads this app's own data directory. Explicit
// config/legacy CLI arguments remain available for controlled native tests.
Startup read_startup(int argc, char ** argv);
} // namespace qwen_app
