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
    if (mode != "monitor-validation")
        throw std::runtime_error("Full-model console inference has not passed its preceding qualification stages");
    if (native_display)
        throw std::runtime_error("The first native BF16 fixture must run without display ownership");
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
}
}
