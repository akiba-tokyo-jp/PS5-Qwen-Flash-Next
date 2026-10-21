// SPDX-License-Identifier: MIT
#include "http_app.h"
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
    if (argc != 5 || std::string(argv[1]) != "--demo") {
        std::cerr << "Usage: app-demo --demo ASSETS CHAT_TEMPLATE PORT\n"
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
        std::cout << "Demo backend; no model loaded. Preview: http://127.0.0.1:" << port << std::endl;
        return qwen_app::serve_http(engine, argv[2], source, port, true);
    } catch (const std::exception & error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
