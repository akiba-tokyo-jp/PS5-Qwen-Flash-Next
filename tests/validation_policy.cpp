// SPDX-License-Identifier: MIT
#include "validation_policy.h"
#include <cassert>
#include <iostream>
using Json = nlohmann::json;
int main() {
    const Json valid = {{"native_BF16_validation", {
        {"schema", "ps5-qwen-native-bf16-validation-v1"},
        {"driver_revision", "872cc1264ad8ba5d6b888b092968fa5858a38c58"},
        {"profile", "cumulative-idle"},
        {"native_archive_sha256", "b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"},
        {"restored_original_SELF_sha256", "2da5c0851cdebe83225edc054f3daf7e4aecd408d3893a9171eb4ad43a22d92d"},
        {"original_numerical_readmission_passed", true},
        {"fresh_idle_session_bound_by_launcher", true},
        {"model_loading_enabled", false}, {"persistent_caches_enabled", false},
        {"fixture", "BF16-32x16-F32-vector"}, {"maximum_graph_compute_calls", 1}}}};
    qwen_app::require_native_validation_policy(valid, "monitor-validation", false);
    qwen_app::require_native_validation_policy(Json::object(), "display-validation", true);
    qwen_app::require_native_validation_policy(Json::object(), "runtime-validation", false);
    unsigned rejected = 0;
    auto reject = [&](const Json & value, const std::string & mode = "monitor-validation", bool display = false) {
        bool caught = false;
        try { qwen_app::require_native_validation_policy(value, mode, display); }
        catch (const std::exception &) { caught = true; }
        assert(caught); ++rejected;
    };
    reject(Json::object());
    reject({{"native_BF16_validation", Json::array()}});
    for (auto field = valid.at("native_BF16_validation").begin(); field != valid.at("native_BF16_validation").end(); ++field) {
        Json changed = valid;
        changed["native_BF16_validation"].erase(field.key());
        reject(changed);
        changed = valid;
        changed["native_BF16_validation"][field.key()] = nullptr;
        reject(changed);
    }
    for (const auto * key : {"schema", "driver_revision", "profile", "native_archive_sha256",
                            "restored_original_SELF_sha256", "fixture"}) {
        auto changed = valid; changed["native_BF16_validation"][key] = "incorrect"; reject(changed);
    }
    for (const auto * key : {"original_numerical_readmission_passed", "fresh_idle_session_bound_by_launcher",
                            "model_loading_enabled", "persistent_caches_enabled"}) {
        auto changed = valid;
        const bool prior = changed["native_BF16_validation"][key].get<bool>();
        changed["native_BF16_validation"][key] = !prior; reject(changed);
        changed["native_BF16_validation"][key] = prior ? 1 : 0; reject(changed);
    }
    for (const Json & count : {Json(0), Json(2), Json(-1), Json(1.0), Json(true), Json("1")}) {
        auto changed = valid; changed["native_BF16_validation"]["maximum_graph_compute_calls"] = count; reject(changed);
    }
    reject(valid, "monitor-validation", true);
    reject(valid, "inference");
    reject(valid, "unrecognized");
    auto arbitrary = valid;
    arbitrary["allowed_modes"] = {"inference", "monitor-validation"};
    arbitrary["console_operations_enabled"] = true;
    arbitrary["deployment_enabled"] = true;
    reject(arbitrary, "inference");
    std::cout << "native_validation_policy_passed rejected_cases=" << rejected
              << " full_inference_rejected=1 GPU_calls=0\n";
}
