// SPDX-License-Identifier: MIT
// Emit and validate the exact native scope with caller-supplied input bindings.
// This is an offline configuration tool, never a console launcher.
#include "first_generation_policy.h"
#include <fstream>
#include <iostream>

int main(int argc, char ** argv) {
    try {
        if (argc != 2) throw std::runtime_error("Expected one original-input binding JSON file");
        std::ifstream input(argv[1]);
        if (!input) throw std::runtime_error("The input binding is absent");
        const auto binding = nlohmann::json::parse(input);
        auto scope = qwen_app::first_generation_scope();
        for (const auto * key : {"candidate_SELF_sha256", "candidate_SELF_bytes", "model_receipt_sha256", "model_receipt_bytes", "run_id"})
            scope[key] = binding.at(key);
        if (binding.contains("prior_native_integrity")) {
            const auto & prior = binding.at("prior_native_integrity");
            if (!prior.is_object() || prior.at("schema") != "ps5-qwen-prior-native-integrity-v1")
                throw std::runtime_error("Unknown prior native integrity evidence");
            scope["prior_native_integrity"] = prior;
        }
        if (binding.contains("allow_app0_model_device_translation")) {
            if (!binding.at("allow_app0_model_device_translation").is_boolean())
                throw std::runtime_error("The app0 device namespace policy must be boolean");
            scope["allow_app0_model_device_translation"] = binding.at("allow_app0_model_device_translation");
        }
        nlohmann::json policy{{"native_first_generation_validation", scope}};
        qwen_app::require_first_generation_policy(policy, false);
        std::cout << scope.dump(2) << '\n';
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
