// SPDX-License-Identifier: MIT
#include "startup.h"
#include "moe_admission.h"
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
        if (data.contains("clock_calibration")) {
            const auto & clock = data.at("clock_calibration");
            if (!clock.is_object() || clock.at("schema") != "ps5-qwen-clock-offset-v1")
                throw std::invalid_argument("Unknown monitor clock calibration schema");
            auto integer = [&](const char * key) {
                const auto & value = clock.at(key);
                if (!value.is_number_integer() || value < 0 || value > 4102444800000LL)
                    throw std::invalid_argument("Monitor clock calibration requires bounded integer fields");
                return value.get<std::int64_t>();
            };
            result.clock_calibration = ClockCalibration{integer("console_epoch_ms"),
                integer("utc_epoch_ms"), integer("uncertainty_ms")};
        }
        const auto mode = data.value("mode", std::string("inference"));
        if (mode != "inference" && mode != "monitor-validation" && mode != "display-validation" && mode != "runtime-validation" && mode != "native-memory-validation" && mode != "model-validation" && mode != "operator-validation" && mode != "moe-validation" && mode != "first-generation-validation")
            throw std::invalid_argument("Unknown application mode");
        result.monitor_validation = mode == "monitor-validation";
        result.display_validation = mode == "display-validation";
        result.runtime_validation = mode == "runtime-validation";
        result.memory_validation = mode == "native-memory-validation";
        if(result.memory_validation && result.native_display)
            throw std::invalid_argument("Native memory validation requires display disabled");
        result.model_validation = mode == "model-validation";
        result.operator_validation = mode == "operator-validation";
        result.moe_validation = mode == "moe-validation";
        result.first_generation_validation = mode == "first-generation-validation";
        if (result.operator_validation || result.moe_validation) {
            result.weight_fixture = data.at("weight_fixture").get<std::string>();
            if (result.weight_fixture != (result.moe_validation ? moe_fixture_path : "/app0/qwen-runtime/original-weight-fixture.bf16"))
                throw std::invalid_argument("The fixed original weight diagnostic path is required");
        } else if (data.contains("weight_fixture")) {
            throw std::invalid_argument("Original weight diagnostics require their bounded validation mode");
        }
        if (result.moe_validation && result.native_display)
            throw std::invalid_argument("MoE validation requires native display disabled");
        if (result.first_generation_validation && result.native_display)
            throw std::invalid_argument("First generation requires native display disabled");
        result.vulkan_global_discovery = data.value("vulkan_global_discovery", false);
        if (result.vulkan_global_discovery && !result.runtime_validation)
            throw std::invalid_argument("Global-only Vulkan discovery requires runtime-validation");
        result.admission_report = data.value("admission_report", result.admission_report);
    }
    for (const auto * path : {&result.development_policy, &result.model_receipt, &result.web_assets, &result.admission_report})
        if (path->empty() || path->size() > 1024 || path->find('\0') != std::string::npos)
            throw std::invalid_argument("Invalid application data path");
    if (result.port < 1024 || result.port > 65535) throw std::invalid_argument("Invalid HTTP port");
    return result;
}
} // namespace qwen_app
