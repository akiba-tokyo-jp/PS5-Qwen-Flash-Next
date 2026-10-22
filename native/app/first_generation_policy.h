// SPDX-License-Identifier: MIT
#pragma once
#include "first_generation.h"
#include <nlohmann/json.hpp>

namespace qwen_app {
inline void require_first_generation_policy(const nlohmann::json & policy, bool native_display) {
    const auto & gate = policy.at("native_first_generation_validation");
    if (native_display || !gate.is_object())
        throw std::runtime_error("First generation requires its no-display private admission");
    const nlohmann::json expected = {
        {"schema", "ps5-qwen-first-generation-v1"},
        {"preceding_moe_SELF_sha256", "0b187cac25c3e322bd4244474a935d191ce85b7bcbb3d2559ead26f05198d057"},
        {"driver_revision", "872cc1264ad8ba5d6b888b092968fa5858a38c58"},
        {"profile", "cumulative-idle"},
        {"native_archive_sha256", "b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"},
        {"original_revision", "de4b8e4d43b917e7706784d8bb445c9af86a3540"},
        {"preceding_moe_passed", true},
        {"original_restoration_and_numerical_readmission_passed", true},
        {"fresh_idle_session_bound_by_launcher", true},
        {"complete_transfer_and_data_lease_bound_by_launcher", true},
        {"complete_v2_model_receipt_required", true},
        {"native_integrity_and_mapping_before_backend_required", true},
        {"persistent_caches_enabled", false}, {"external_requests_enabled", false},
        {"maximum_requests", 1}, {"maximum_context_tokens", first_context_tokens},
        {"maximum_prompt_tokens", first_prompt_tokens}, {"maximum_output_tokens", first_output_tokens},
        {"maximum_generation_seconds", first_generation_seconds},
        {"maximum_verification_seconds", 7200}, {"maximum_model_load_seconds", 1200},
        {"maximum_context_creation_seconds", 600}, {"maximum_mapped_bytes", 512ull << 30},
        {"prompt", first_generation_prompt}, {"enable_thinking", false}};
    for (auto item = expected.begin(); item != expected.end(); ++item) {
        const auto & actual = gate.at(item.key());
        const auto & wanted = item.value();
        const bool integer = wanted.is_number_integer();
        if ((integer && !actual.is_number_integer()) ||
            (!integer && actual.type() != wanted.type()) || actual != wanted)
            throw std::runtime_error("First-generation policy exceeds its exact admitted scope");
    }
    auto digest = [&](const char * key) {
        const auto & value = gate.at(key);
        if (!value.is_string()) throw std::runtime_error("First-generation provenance digest is required");
        const auto text = value.get<std::string>();
        if (text.size() != 64 || text.find_first_not_of("0123456789abcdef") != std::string::npos)
            throw std::runtime_error("First-generation provenance digest is invalid");
    };
    digest("candidate_SELF_sha256"); digest("model_receipt_sha256");
    for (const auto * key : {"candidate_SELF_bytes", "model_receipt_bytes"}) {
        const auto & bytes = gate.at(key);
        const auto maximum = std::string(key) == "candidate_SELF_bytes" ? (128ull << 20) : (16ull << 20);
        if (!bytes.is_number_integer() || bytes <= 0 || bytes > maximum)
            throw std::runtime_error("First-generation input byte count is invalid");
    }
    const auto id = gate.at("run_id").get<std::string>();
    if (id.size() != 32 || id.find_first_not_of("0123456789abcdef") != std::string::npos)
        throw std::runtime_error("First generation requires a fresh bounded run identity");
}
}
