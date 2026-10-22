// SPDX-License-Identifier: MIT
#include "startup.h"
#include "nlohmann/json.hpp"
#include <fstream>
#include <stdexcept>

namespace qwen_app {
Startup read_startup(int argc, char ** argv) {
    Startup result;
    if (argc == 5) {
        result.development_policy = argv[1]; result.model_receipt = argv[2]; result.web_assets = argv[3];
        std::size_t length = 0; result.port = std::stoi(argv[4], &length);
        if (length != std::string(argv[4]).size()) throw std::invalid_argument("Invalid HTTP port");
    } else {
        if (argc > 2) throw std::invalid_argument("Usage: app-native [APP_CONFIG]");
        const std::string path = argc == 2 ? argv[1] : "/app0/qwen-runtime/app.json";
        std::ifstream file(path, std::ios::binary);
        if (!file) throw std::runtime_error("Application startup configuration was not found");
        file.seekg(0, std::ios::end); const auto bytes = file.tellg(); file.seekg(0);
        if (bytes < 0 || bytes > 16384) throw std::runtime_error("Application configuration exceeds its bound");
        const auto data = nlohmann::json::parse(file);
        if (data.at("schema") != "ps5-qwen-app-v1") throw std::invalid_argument("Unknown application configuration schema");
        result.development_policy = data.at("development_policy").get<std::string>();
        result.model_receipt = data.at("model_receipt").get<std::string>();
        result.web_assets = data.at("web_assets").get<std::string>();
        result.port = data.value("port", 8086);
        result.native_display = data.value("native_display", true);
        const auto mode = data.value("mode", std::string("inference"));
        if (mode != "inference" && mode != "monitor-validation" && mode != "display-validation")
            throw std::invalid_argument("Unknown application mode");
        result.monitor_validation = mode == "monitor-validation";
        result.display_validation = mode == "display-validation";
        result.admission_report = data.value("admission_report", result.admission_report);
    }
    for (const auto * path : {&result.development_policy, &result.model_receipt, &result.web_assets, &result.admission_report})
        if (path->empty() || path->size() > 1024 || path->find('\0') != std::string::npos)
            throw std::invalid_argument("Invalid application data path");
    if (result.port < 1024 || result.port > 65535) throw std::invalid_argument("Invalid HTTP port");
    return result;
}
} // namespace qwen_app
