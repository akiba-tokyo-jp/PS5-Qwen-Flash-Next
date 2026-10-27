// SPDX-License-Identifier: MIT
#pragma once
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace qwen_app {
inline void require_model_free_speculation_policy(const nlohmann::json &policy) {
    using J=nlohmann::json;
    const auto &p=policy.at("native_model_free_speculation");
    const auto &proof=p.at("complete_checkpoint_qualification");
    J expected={{"schema","ps5-qwen-causal-width-two-v1"},{"enabled",true},{"target_batch_tokens",2},
        {"candidate_request_ordinal",2},
        {"draft_evidence","two_consistent_past_matches"},{"maximum_attempts_per_process",32},
        {"maximum_generated_tokens_per_request",32},{"context_tokens",256},{"prefill_tokens",4},
        {"active_cache_slots",53},{"learned_draft_model",false},{"greedy_target_verification",true},
        {"complete_state_restore_on_rejection",true},{"automatic_retries",0},
        {"complete_checkpoint_qualification",proof},{"performance_adoption_enabled",false}};
    if(p.contains("verification_policy")) {
        expected["verification_policy"]="expert-union-online-v1";
        if(!policy.contains("native_expert_routes"))
            throw std::runtime_error("Online expert costs require the completed original route observer");
    }
    if(p!=expected||policy.contains("native_large_cache_scope")||policy.contains("native_prefix_validation")||
       policy.contains("native_model_checkpoint_validation")||policy.contains("native_predictive_cache")||!policy.contains("native_padded_expert_cache")||
       policy.at("native_prefill").at("tokens")!=4)
        throw std::runtime_error("The independent original-precision causal width-two experimental scope is required");
    const auto run=proof.at("run_id").get<std::string>();
    if(proof.size()!=5||run.size()!=32||run.find_first_not_of("0123456789abcdef")!=std::string::npos||
       proof.at("report_path")!="/app0/qwen-runtime/plan-"+run+".json.model-checkpoint"||
       proof.at("report_bytes")!=1137||!proof.at("pid").is_number_integer()||proof.at("pid")<=0||
       proof.at("report_sha256")!="e9d0db6bfb5b2d090e021c972cf14728f3a7d96b956c03b08946a60d6fdb50d7")
        throw std::runtime_error("The exact positively completed native full-state checkpoint qualification is required");
}
inline void require_model_free_checkpoint_report(const nlohmann::json &r,const nlohmann::json &proof) {
    if(r.at("schema")!="ps5-qwen-model-checkpoint-validation-result-v1"||r.at("pid")!=proof.at("pid")||
       r.at("run_id")!=proof.at("run_id")||r.at("captures")!=25||r.at("restores")!=25||
       r.at("prefill_replays")!=2||r.at("next_replays_including_EOG")!=23||
       r.at("original_route_rows_compared")!=1152||r.at("maximum_absolute_logit_error")!=0||
       r.at("all_original_expert_selections_exact")!=true||r.at("all_continuation_tokens_and_bytes_exact")!=true||
       r.at("device_ledger_live_bytes")!=0||r.at("all_model_source_and_checkpoint_owners_retired")!=true)
        throw std::runtime_error("Complete original native checkpoint continuation and retirement have not been established");
}
}
