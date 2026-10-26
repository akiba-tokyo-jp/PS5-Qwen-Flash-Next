// SPDX-License-Identifier: MIT
#pragma once
#include <stdexcept>
#include <string>
#include <nlohmann/json.hpp>
#include "operator_admission.h"
#include "moe_admission.h"
#include "first_generation_policy.h"
#include "memory_probe.h"
#include "palette_gpu_admission.h"
#include "vector_bank_admission.h"
#include "device_state_admission.h"
#include "ple_slice_admission.h"
#include "model_checkpoint_policy.h"
#include "prefix_validation_policy.h"
#include "metadata_memory_policy.h"

namespace qwen_app {
inline constexpr unsigned native_model_verification_seconds = 7200;
// A private, frozen fixture policy is also bound to the exact SELF and fresh
// session by the ordinary OS launcher. This checks scope, not console health.
inline void require_native_validation_policy(const nlohmann::json & policy,
                                             const std::string & mode,
                                             bool native_display) {
    if (mode == "display-validation" || mode == "runtime-validation") return;
    if (mode == "palette-validation") {require_palette_gpu_policy(policy,native_display);return;}
    if (mode == "vector-bank-validation") {require_vector_bank_policy(policy,native_display);return;}
    if (mode == "device-state-validation") {require_device_state_policy(policy,native_display);return;}
    if (mode == "PLE-slice-validation") {require_PLE_slice_policy(policy,native_display);return;}
    if (mode == "native-memory-validation") {
        require_memory_probe_policy(policy,native_display);return;
    }
    if (mode == "first-generation-validation") {
        require_first_generation_policy(policy, native_display);
        if(policy.contains("native_model_checkpoint_validation"))require_model_checkpoint_policy(policy);
        if(policy.contains("native_prefix_validation"))require_prefix_validation_policy(policy);
        if(policy.contains("native_metadata_memory_diagnostic"))require_metadata_memory_policy(policy);
        return;
    }
    if (mode == "moe-validation") {
        const auto & moe = policy.at("native_moe_validation");
        if (native_display || !moe.is_object() ||
            moe.at("schema") != "ps5-qwen-native-moe-validation-v1" ||
            moe.at("preceding_operator_SELF_sha256") != "5abd9fab586ed30431ddf26a95a1a112065f2958c6cbbd0a41b107a62c67da47" ||
            moe.at("driver_revision") != "872cc1264ad8ba5d6b888b092968fa5858a38c58" ||
            moe.at("profile") != "cumulative-idle" ||
            moe.at("native_archive_sha256") != "b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925" ||
            moe.at("original_revision") != "de4b8e4d43b917e7706784d8bb445c9af86a3540" ||
            moe.at("source_shard_sha256") != "1da92de7cf72dcca86faf05007925389ceb24427609e8d3b478d53d97fd97a63" ||
            moe.at("fixture_sha256") != moe_fixture_sha256 ||
            moe.at("original_restoration_and_numerical_readmission_passed") != true ||
            moe.at("fresh_idle_session_bound_by_launcher") != true ||
            moe.at("model_loading_enabled") != false || moe.at("persistent_caches_enabled") != false ||
            !moe.at("maximum_graph_compute_calls").is_number_integer() || moe.at("maximum_graph_compute_calls") != 1 ||
            !moe.at("fixture_bytes").is_number_integer() || moe.at("fixture_bytes") != moe_fixture_bytes ||
            !moe.at("experts").is_number_integer() || moe.at("experts") != moe_experts ||
            !moe.at("selected_experts").is_number_integer() || moe.at("selected_experts") != moe_selected ||
            !moe.at("maximum_upload_chunk_bytes").is_number_integer() || moe.at("maximum_upload_chunk_bytes") != (8u << 20))
            throw std::runtime_error("The exact no-display original BF16 MoE diagnostic policy is required");
        const auto & ids = moe.at("expert_ids");
        if (!ids.is_array() || ids.size() != moe_selected)
            throw std::runtime_error("The complete fixed MoE expert ID sequence is required");
        for (unsigned i = 0; i < moe_selected; ++i)
            if (!ids.at(i).is_number_integer() || ids.at(i) != moe_expert_ids[i])
                throw std::runtime_error("The fixed MoE expert ID order is required");
        return;
    }
    if (mode == "operator-validation") {
        const auto & ops = policy.at("native_operator_validation");
        if (native_display || !ops.is_object() ||
            ops.at("schema") != "ps5-qwen-native-operator-validation-v1" ||
            ops.at("preceding_combined_SELF_sha256") != "54c2803c6fce4a654f5c351878eb717dfa0f58c874868b14c0d868fa7630fea9" ||
            ops.at("driver_revision") != "872cc1264ad8ba5d6b888b092968fa5858a38c58" ||
            ops.at("profile") != "cumulative-idle" ||
            ops.at("native_archive_sha256") != "b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925" ||
            ops.at("original_revision") != "de4b8e4d43b917e7706784d8bb445c9af86a3540" ||
            ops.at("source_shard_sha256") != "1da92de7cf72dcca86faf05007925389ceb24427609e8d3b478d53d97fd97a63" ||
            ops.at("fixture_sha256") != original_weight_fixture_sha256 ||
            ops.at("original_restoration_and_numerical_readmission_passed") != true ||
            ops.at("fresh_idle_session_bound_by_launcher") != true ||
            ops.at("model_loading_enabled") != false || ops.at("persistent_caches_enabled") != false ||
            !ops.at("maximum_graph_compute_calls").is_number_integer() || ops.at("maximum_graph_compute_calls") != 1 ||
            !ops.at("fixture_bytes").is_number_integer() || ops.at("fixture_bytes") != 81920)
            throw std::runtime_error("The exact no-display original-weight operation policy is required");
        return;
    }
    if (mode == "model-validation") {
        const auto & model = policy.at("native_model_validation");
        if (native_display || !model.is_object() ||
            model.at("schema") != "ps5-qwen-native-model-validation-v2" ||
            model.at("preceding_combined_SELF_sha256") != "54c2803c6fce4a654f5c351878eb717dfa0f58c874868b14c0d868fa7630fea9" ||
            model.at("preceding_CPU_hash_probe_ELF_sha256") != "cbd7964f9b46e9e817bce99a53228058a0183d12cda901755fb4c3d13f2f181b" ||
            model.at("preceding_CPU_hash_probe_passed") != true ||
            model.at("original_restoration_and_numerical_readmission_passed") != true ||
            model.at("fresh_idle_session_bound_by_launcher") != true ||
            model.at("complete_v2_model_receipt_required") != true ||
            model.at("Vulkan_initialization_enabled") != false ||
            model.at("model_loading_enabled") != false ||
            !model.at("maximum_verification_seconds").is_number_integer() ||
            model.at("maximum_verification_seconds") != native_model_verification_seconds ||
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
