// SPDX-License-Identifier: MIT
#pragma once
#include "model_integrity.h"
#include "mapped_source.h"
#include "nlohmann/json.hpp"
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace qwen_app {
struct PriorModelIntegrity {
    std::vector<SourceIdentity> files;
    SourceIdentity receipt{}, directory{};
    std::string report_sha256, snapshot_sha256;
    std::uint64_t original_elapsed_ms = 0;
};
inline std::optional<PriorModelIntegrity> prior_model_integrity(const nlohmann::json & gate,
        const nlohmann::json & receipt, std::uint64_t total_bytes) {
    if (!gate.contains("prior_native_integrity")) return {};
    const auto & evidence = gate.at("prior_native_integrity");
    auto require = [](bool value) { if (!value) throw std::runtime_error("Prior native integrity and sealed-file evidence is not admitted"); };
    require(evidence.is_object() && evidence.at("schema") == "ps5-qwen-prior-native-integrity-v1");
    auto original = [&](const char * key) {
        const auto & row = evidence.at(key);
        require(row.is_object() && row.at("raw").is_string() && row.at("sha256").is_string());
        const auto raw = row.at("raw").get<std::string>();
        require(sha256_metadata_bytes(raw) == row.at("sha256").get<std::string>());
        return nlohmann::json::parse(raw);
    };
    const auto report = original("integrity_report"), start = original("native_start"), snapshot = original("snapshot");
    require(report.at("schema") == "ps5-qwen-model-integrity-v1" && report.at("all_SHA256_matched") == true &&
        report.at("files_verified") == receipt.at("files").size() && report.at("verified_file_bytes") == total_bytes &&
        report.at("mapped_file_bytes") == total_bytes && report.at("Vulkan_initialized") == false && report.at("model_loaded") == false &&
        report.at("maximum_verification_seconds") == 7200 && report.at("verification_elapsed_ms").is_number_integer() &&
        report.at("verification_elapsed_ms") > 0 && report.at("verification_elapsed_ms") <= 7200000);
    require(start.at("schema") == "ps5-qwen-first-generation-start-v1" && start.at("pid") == report.at("pid") &&
        start.at("model_receipt_sha256") == gate.at("model_receipt_sha256") && start.at("model_loaded") == false &&
        start.at("Vulkan_initialized") == false && start.at("candidate_SELF_sha256") == evidence.at("prior_candidate_SELF_sha256"));
    const auto previous = evidence.at("prior_candidate_SELF_sha256").get<std::string>();
    require(previous.size() == 64 && previous.find_first_not_of("0123456789abcdef") == std::string::npos);
    require(snapshot.at("schema") == "ps5-qwen-sealed-model-identity-snapshot-v1" &&
        snapshot.at("all_ctimes_no_later_than_sealing") == true && snapshot.at("directory_unchanged_since_sealing") == true &&
        snapshot.at("model_payload_reads") == 0 && snapshot.at("mappings") == 0 &&
        snapshot.at("files").is_array() && snapshot.at("files").size() == receipt.at("files").size() + 1);
    auto identity = [&](const nlohmann::json & row) {
        require(row.is_array() && row.size() == 10); SourceIdentity result{};
        for (unsigned i = 0; i < result.size(); ++i) {
            require(row.at(i).is_number_integer() && row.at(i) >= 0); result[i] = row.at(i).get<std::uint64_t>();
        }
        require(result[0] && result[1] && result[5] && result[6] <= 4102444800ull && result[8] <= 4102444800ull &&
            result[7] < 1000000000 && result[9] < 1000000000);
        return result;
    };
    const auto seal = identity(snapshot.at("seal_evidence_identity"));
    const auto old_report = identity(snapshot.at("native_integrity_evidence_identity"));
    auto no_later = [](const SourceIdentity & a, unsigned i, const SourceIdentity & b, unsigned j) {
        return a[i] < b[j] || (a[i] == b[j] && a[i + 1] <= b[j + 1]);
    };
    require((seal[2] & 0177777) == 0100600 && seal[3] == 0 && seal[4] == 0 &&
        old_report[3] == 1 && (old_report[2] & 0177777) == 0100644 && no_later(seal, 6, old_report, 6) &&
        old_report[5] == evidence.at("integrity_report").at("raw").get<std::string>().size());
    PriorModelIntegrity result;
    result.directory = identity(snapshot.at("directory_identity"));
    require((result.directory[2] & 0177777) == 0040755 && result.directory[3] == 0 && result.directory[4] == 0 &&
        no_later(result.directory, 6, seal, 6) && no_later(result.directory, 8, seal, 6));
    for (std::size_t i = 0; i < snapshot.at("files").size(); ++i) {
        const auto & row = snapshot.at("files").at(i); const auto value = identity(row.at("identity"));
        const bool is_receipt = i == receipt.at("files").size();
        const auto wanted_path = is_receipt ? std::string("model-receipt.json") : receipt.at("files").at(i).at("path").get<std::string>();
        const auto wanted_bytes = is_receipt ? gate.at("model_receipt_bytes").get<std::uint64_t>() : receipt.at("files").at(i).at("bytes").get<std::uint64_t>();
        require(row.at("path") == wanted_path && value[5] == wanted_bytes && (value[2] & 0177777) == 0100644 &&
            value[3] == 0 && value[4] == 0 && no_later(value, 8, seal, 6) && no_later(value, 6, value, 8));
        for (const auto & previous_value : result.files) require(value[0] != previous_value[0] || value[1] != previous_value[1]);
        if (is_receipt) result.receipt = value; else result.files.push_back(value);
    }
    result.report_sha256 = evidence.at("integrity_report").at("sha256").get<std::string>();
    result.snapshot_sha256 = evidence.at("snapshot").at("sha256").get<std::string>();
    result.original_elapsed_ms = report.at("verification_elapsed_ms").get<std::uint64_t>();
    return result;
}
}
