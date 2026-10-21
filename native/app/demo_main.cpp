// SPDX-License-Identifier: MIT
#include "http_app.h"
#include "nlohmann/json.hpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <thread>

class DemoEngine final : public qwen_app::Engine {
    std::size_t index_ = 0;
    const std::string text_ = "Demo only: this response verifies the application stream. No model is loaded.\n";
public:
    std::uint32_t tokenize(const std::string & prompt) override {
        return std::uint32_t((prompt.size() + 3) / 4);
    }
    void prefill(std::uint32_t) override { index_ = 0; }
    qwen_app::Token next() override {
        std::this_thread::sleep_for(std::chrono::milliseconds(25));
        if (index_ == text_.size()) return {0, {}, true};
        const auto id = std::int32_t(index_++);
        return {id, text_.substr(std::size_t(id), 1), false};
    }
    void finish() override {}
};

int main(int argc, char ** argv) {
    if ((argc != 5 && argc != 6) || (std::string(argv[1]) != "--demo" && std::string(argv[1]) != "--monitor-demo")) {
        std::cerr << "Usage: app-demo --demo|--monitor-demo ASSETS CHAT_TEMPLATE PORT [MONITOR_LOG]\n"
                     "Development preview only; console release remains disabled.\n";
        return 2;
    }
    try {
        std::ifstream stream(argv[3], std::ios::binary);
        if (!stream) throw std::runtime_error("Pinned chat template not found");
        std::string source((std::istreambuf_iterator<char>(stream)), {});
        const int port = std::stoi(argv[4]);
        if (port < 1024 || port > 65535) throw std::invalid_argument("Invalid preview port");
        DemoEngine engine;
        std::function<void(const qwen_app::MonitorSnapshot &)> observer;
        if (argc == 6) {
            const std::string path = argv[5];
            observer = [path](const qwen_app::MonitorSnapshot & value) {
                std::ofstream log(path, std::ios::app);
                log << nlohmann::json({{"epoch_ms", value.epoch_ms}, {"busy", value.busy},
                    {"model_loaded", value.model_loaded}, {"generated_tokens", value.generated_tokens},
                    {"state", value.state}, {"message", value.message}}).dump() << '\n';
            };
        }
        std::cout << "Demo backend; no model loaded. Preview: http://127.0.0.1:" << port << std::endl;
        return qwen_app::serve_http(engine, argv[2], source, port, true, {}, observer,
                                    std::string(argv[1]) == "--monitor-demo");
    } catch (const std::exception & error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
