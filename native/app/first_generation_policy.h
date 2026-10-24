// SPDX-License-Identifier: MIT
#pragma once
#include "first_generation.h"
#include "model_cpu_budget.h"
#include <nlohmann/json.hpp>

namespace qwen_app {
inline nlohmann::json first_generation_scope() {
    return {
        {"schema", "ps5-qwen-first-generation-v4"},
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
        {"bounded_mapped_source_reads_required", true}, {"source_window_bytes", 8u << 20},
        {"reserved_virtual_sources_required", true}, {"file_backed_model_mmap_enabled", false},
        {"bounded_original_CPU_rows_required", true}, {"maximum_CPU_source_row_bytes", 1u << 20},
        {"maximum_source_handles", 8}, {"CPU_matrix_fallback_enabled", false},
        {"maximum_CPU_workspace_bytes", 16u << 20},
        {"persistent_caches_enabled", false}, {"unrestricted_external_requests_enabled", false},
        {"maximum_requests", 1}, {"maximum_context_tokens", first_context_tokens},
        {"bounded_demonstration_required", true}, {"demonstration_external_requests", 2},
        {"demonstration_listener_bind", "0.0.0.0"}, {"demonstration_listener_port", 8086},
        {"native_display_after_first_request_required", true}, {"maximum_display_buffer_bytes", 32u << 20},
        {"demonstration_idle_deadline_seconds", 900}, {"demonstration_total_deadline_seconds", 10800},
        {"recreate_completed_context_before_benchmark_required", true}, {"model_reload_before_benchmark_enabled", false},
        {"CPU_budget_bytes", model_CPU_budget_bytes},
        {"maximum_explicitly_addressed_CPU_model_page_bytes", maximum_addressed_model_CPU_bytes},
        {"maximum_CPU_heap_bytes", maximum_model_CPU_heap_bytes},
        {"maximum_resident_CPU_model_source_bytes", maximum_resident_model_CPU_source_bytes},
        {"CPU_heap_budget_includes_source_read_window", true},
        {"source_window_must_be_in_Direct_CPU_heap", true},
        {"graph_workspace_budget_bytes", 256ull << 20},
        {"maximum_postload_device_buffer_bytes", 512ull << 20},
        {"maximum_aggregate_postload_device_buffer_bytes", 1792ull << 20},
        {"maximum_prompt_tokens", first_prompt_tokens}, {"maximum_output_tokens", first_output_tokens},
        {"maximum_generation_seconds", first_generation_seconds},
        {"maximum_verification_seconds", 7200}, {"maximum_model_load_seconds", 1200},
        {"maximum_context_creation_seconds", 600}, {"maximum_mapped_bytes", 512ull << 30},
        {"prompt", first_generation_prompt}, {"enable_thinking", false}};
}
inline void require_first_generation_policy(const nlohmann::json & policy, bool native_display) {
    const auto & gate = policy.at("native_first_generation_validation");
    if (native_display || !gate.is_object())
        throw std::runtime_error("First generation requires its no-display private admission");
    const auto expected = first_generation_scope();
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
