// SPDX-License-Identifier: MIT
// Host metadata validation through the actual native receipt gate. No model I/O.
#include "model_receipt.h"
#include <iostream>
int main(int argc, char ** argv) {
    try {
        if (argc != 2) throw std::invalid_argument("One completed original model receipt is required");
        const auto receipt = qwen_app::read_model_receipt(argv[1]);
        const auto total = qwen_app::validate_model_receipt(receipt);
        std::cout << nlohmann::json{{"native_receipt_gate_passed", true},
            {"mapped_file_bytes", total}, {"files", receipt.at("files").size()},
            {"model_loaded", false}, {"console_access", false}}.dump() << '\n';
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
