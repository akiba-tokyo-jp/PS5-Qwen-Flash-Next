// SPDX-License-Identifier: MIT
#pragma once
#include <stdexcept>
#include <string>
#include <nlohmann/json.hpp>

namespace qwen_app {
// A private, frozen fixture policy is also bound to the exact SELF and fresh
// session by the ordinary OS launcher. This checks scope, not console health.
inline void require_native_validation_policy(const nlohmann::json & policy,
                                             const std::string & mode,
                                             bool native_display) {
    if (mode == "display-validation" || mode == "runtime-validation") return;
    if (mode == "model-validation") {
        const auto & model = policy.at("native_model_validation");
        if (native_display || !model.is_object() ||
            model.at("schema") != "ps5-qwen-native-model-validation-v1" ||
            model.at("preceding_combined_SELF_sha256") != "54c2803c6fce4a654f5c351878eb717dfa0f58c874868b14c0d868fa7630fea9" ||
            model.at("original_restoration_and_numerical_readmission_passed") != true ||
            model.at("fresh_idle_session_bound_by_launcher") != true ||
            model.at("complete_v2_model_receipt_required") != true ||
            model.at("Vulkan_initialization_enabled") != false ||
            model.at("model_loading_enabled") != false ||
            !model.at("maximum_verification_seconds").is_number_integer() ||
            model.at("maximum_verification_seconds") != 1800 ||
            !model.at("maximum_mapped_bytes").is_number_integer() ||
            model.at("maximum_mapped_bytes") != (512ull << 30))
            throw std::runtime_error("The exact no-GPU original model validation policy is required");
        return;
    }
    if (mode != "monitor-validation")
        throw std::runtime_error("Full-model console inference has not passed its preceding qualification stages");
    const auto & fixture = policy.at("native_BF16_validation");
    if (!fixture.is_object() ||
        fixture.at("schema") != "ps5-qwen-native-bf16-validation-v1" ||
        fixture.at("driver_revision") != "872cc1264ad8ba5d6b888b092968fa5858a38c58" ||
        fixture.at("profile") != "cumulative-idle" ||
        fixture.at("native_archive_sha256") != "b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925" ||
        fixture.at("restored_original_SELF_sha256") != "2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d" ||
        fixture.at("original_numerical_readmission_passed") != true ||
        fixture.at("fresh_idle_session_bound_by_launcher") != true ||
        fixture.at("model_loading_enabled") != false ||
        fixture.at("persistent_caches_enabled") != false ||
        fixture.at("fixture") != "BF16-32x16-F32-vector" ||
        !fixture.at("maximum_graph_compute_calls").is_number_integer() ||
        fixture.at("maximum_graph_compute_calls") != 1)
        throw std::runtime_error("The exact bounded native BF16 fixture policy is required");
    if (native_display) {
        const auto & display = policy.at("native_display_after_BF16_validation");
        if (!display.is_object() ||
            display.at("schema") != "ps5-qwen-display-after-bf16-v1" ||
            display.at("preceding_SELF_sha256") != "5c808d43cbe49f5d790707cc7fd67055b8de3e4bc1aa860c57ffa30c9ea6d427" ||
            display.at("preceding_BF16_passed") != true ||
            display.at("preceding_completion_and_retirement_passed") != true ||
            display.at("start_only_after_current_BF16_completion") != true ||
            !display.at("maximum_display_buffer_bytes").is_number_integer() ||
            display.at("maximum_display_buffer_bytes") != (32u << 20))
            throw std::runtime_error("Completed BF16 admission is required before native display validation");
    }
}
}
