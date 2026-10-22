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
    auto combined = valid;
    combined["native_display_after_BF16_validation"] = {
        {"schema", "ps5-qwen-display-after-bf16-v1"},
        {"preceding_SELF_sha256", "5c808d43cbe49f5d790707cc7fd67055b8de3e4bc1aa860c57ffa30c9ea6d427"},
        {"preceding_BF16_passed", true}, {"preceding_completion_and_retirement_passed", true},
        {"start_only_after_current_BF16_completion", true}, {"maximum_display_buffer_bytes", 32u << 20}};
    qwen_app::require_native_validation_policy(combined, "monitor-validation", true);
    for (auto field = combined.at("native_display_after_BF16_validation").begin();
         field != combined.at("native_display_after_BF16_validation").end(); ++field) {
        auto changed = combined; changed["native_display_after_BF16_validation"].erase(field.key());
        reject(changed, "monitor-validation", true);
        changed = combined; changed["native_display_after_BF16_validation"][field.key()] = nullptr;
        reject(changed, "monitor-validation", true);
    }
    for (const auto * key : {"preceding_BF16_passed", "preceding_completion_and_retirement_passed",
                            "start_only_after_current_BF16_completion"}) {
        auto changed = combined; changed["native_display_after_BF16_validation"][key] = false;
        reject(changed, "monitor-validation", true);
        changed["native_display_after_BF16_validation"][key] = 1;
        reject(changed, "monitor-validation", true);
    }
    for (const auto * key : {"schema", "preceding_SELF_sha256"}) {
        auto changed = combined; changed["native_display_after_BF16_validation"][key] = "incorrect";
        reject(changed, "monitor-validation", true);
    }
    for (const Json & bytes : {Json(0), Json(64u << 20), Json(33554432.0), Json(true)}) {
        auto changed = combined; changed["native_display_after_BF16_validation"]["maximum_display_buffer_bytes"] = bytes;
        reject(changed, "monitor-validation", true);
    }
    reject(combined, "inference", true);
    const Json model = {{"native_model_validation", {
        {"schema", "ps5-qwen-native-model-validation-v2"},
        {"preceding_combined_SELF_sha256", "54c2803c6fce4a654f5c351878eb717dfa0f58c874868b14c0d868fa7630fea9"},
        {"preceding_CPU_hash_probe_ELF_sha256", "cbd7964f9b46e9e817bce99a53228058a0183d12cda901755fb4c3d13f2f181b"},
        {"preceding_CPU_hash_probe_passed", true},
        {"original_restoration_and_numerical_readmission_passed", true},
        {"fresh_idle_session_bound_by_launcher", true}, {"complete_v2_model_receipt_required", true},
        {"Vulkan_initialization_enabled", false}, {"model_loading_enabled", false},
        {"maximum_verification_seconds", 7200}, {"maximum_mapped_bytes", 512ull << 30}}}};
    qwen_app::require_native_validation_policy(model, "model-validation", false);
    reject(model, "model-validation", true);
    reject(model, "inference");
    for (auto field = model.at("native_model_validation").begin(); field != model.at("native_model_validation").end(); ++field) {
        auto changed = model; changed["native_model_validation"].erase(field.key());
        reject(changed, "model-validation");
        changed = model; changed["native_model_validation"][field.key()] = nullptr;
        reject(changed, "model-validation");
    }
    for (const auto * key : {"preceding_CPU_hash_probe_passed", "original_restoration_and_numerical_readmission_passed", "fresh_idle_session_bound_by_launcher",
                            "complete_v2_model_receipt_required", "Vulkan_initialization_enabled", "model_loading_enabled"}) {
        auto changed = model;
        const bool prior = changed["native_model_validation"][key].get<bool>();
        changed["native_model_validation"][key] = !prior; reject(changed, "model-validation");
        changed["native_model_validation"][key] = prior ? 1 : 0; reject(changed, "model-validation");
    }
    for (const auto * key : {"schema", "preceding_combined_SELF_sha256", "preceding_CPU_hash_probe_ELF_sha256"}) {
        auto changed = model; changed["native_model_validation"][key] = "incorrect"; reject(changed, "model-validation");
    }
    for (const auto * key : {"maximum_verification_seconds", "maximum_mapped_bytes"}) {
        auto changed = model; changed["native_model_validation"][key] = 0; reject(changed, "model-validation");
        changed["native_model_validation"][key] = model["native_model_validation"][key].get<double>();
        reject(changed, "model-validation");
    }
    for(const Json & seconds:{Json(1800),Json(7199),Json(7201),Json(true)}) {
        auto changed=model;changed["native_model_validation"]["maximum_verification_seconds"]=seconds;
        reject(changed,"model-validation");
    }
    auto legacy_model=model;legacy_model["native_model_validation"]["schema"]="ps5-qwen-native-model-validation-v1";
    reject(legacy_model,"model-validation");
    legacy_model["native_model_validation"]["maximum_verification_seconds"]=1800;
    reject(legacy_model,"model-validation");
    const Json operators = {{"native_operator_validation", {
        {"schema", "ps5-qwen-native-operator-validation-v1"},
        {"preceding_combined_SELF_sha256", "54c2803c6fce4a654f5c351878eb717dfa0f58c874868b14c0d868fa7630fea9"},
        {"driver_revision", "872cc1264ad8ba5d6b888b092968fa5858a38c58"}, {"profile", "cumulative-idle"},
        {"native_archive_sha256", "b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"},
        {"original_revision", "de4b8e4d43b917e7706784d8bb445c9af86a3540"},
        {"source_shard_sha256", "1da92de7cf72dcca86faf05007925389ceb24427609e8d3b478d53d97fd97a63"},
        {"fixture_sha256", qwen_app::original_weight_fixture_sha256},
        {"original_restoration_and_numerical_readmission_passed", true}, {"fresh_idle_session_bound_by_launcher", true},
        {"model_loading_enabled", false}, {"persistent_caches_enabled", false},
        {"maximum_graph_compute_calls", 1}, {"fixture_bytes", 81920}}}};
    qwen_app::require_native_validation_policy(operators, "operator-validation", false);
    reject(operators, "operator-validation", true); reject(operators, "inference");
    for (auto field = operators.at("native_operator_validation").begin(); field != operators.at("native_operator_validation").end(); ++field) {
        auto changed = operators; changed["native_operator_validation"].erase(field.key()); reject(changed, "operator-validation");
        changed = operators; changed["native_operator_validation"][field.key()] = nullptr; reject(changed, "operator-validation");
    }
    for (const auto * key : {"schema", "preceding_combined_SELF_sha256", "driver_revision", "profile", "native_archive_sha256",
                            "original_revision", "source_shard_sha256", "fixture_sha256"}) {
        auto changed = operators; changed["native_operator_validation"][key] = "incorrect"; reject(changed, "operator-validation");
    }
    for (const auto * key : {"original_restoration_and_numerical_readmission_passed", "fresh_idle_session_bound_by_launcher",
                            "model_loading_enabled", "persistent_caches_enabled"}) {
        auto changed = operators; const bool prior = changed["native_operator_validation"][key].get<bool>();
        changed["native_operator_validation"][key] = !prior; reject(changed, "operator-validation");
        changed["native_operator_validation"][key] = prior ? 1 : 0; reject(changed, "operator-validation");
    }
    for (const auto * key : {"maximum_graph_compute_calls", "fixture_bytes"}) {
        auto changed = operators; changed["native_operator_validation"][key] = 0; reject(changed, "operator-validation");
        changed["native_operator_validation"][key] = operators["native_operator_validation"][key].get<double>();
        reject(changed, "operator-validation");
    }
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
