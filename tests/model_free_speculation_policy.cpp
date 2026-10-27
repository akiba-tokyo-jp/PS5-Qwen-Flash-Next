// SPDX-License-Identifier: MIT
#include "model_free_speculation_policy.h"
#include <iostream>
using J=nlohmann::json;
static unsigned failures=0;
template<class F>static void refused(F action){bool bad=false;try{action();}catch(const std::exception&){bad=true;}
    if(!bad)throw std::runtime_error("Invalid causal width-two policy admitted");++failures;}
int main(){
    const std::string run(32,'a');
    J proof={{"run_id",run},{"pid",123},{"report_bytes",1137},
        {"report_path","/app0/qwen-runtime/plan-"+run+".json.model-checkpoint"},
        {"report_sha256","e9d0db6bfb5b2d090e021c972cf14728f3a7d96b956c03b08946a60d6fdb50d7"}};
    J scope={{"schema","ps5-qwen-causal-width-two-v1"},{"enabled",true},{"target_batch_tokens",2},
        {"candidate_request_ordinal",2},{"draft_evidence","two_consistent_past_matches"},
        {"maximum_attempts_per_process",32},{"maximum_generated_tokens_per_request",32},{"context_tokens",256},
        {"prefill_tokens",4},{"active_cache_slots",53},{"learned_draft_model",false},
        {"greedy_target_verification",true},{"complete_state_restore_on_rejection",true},
        {"automatic_retries",0},{"complete_checkpoint_qualification",proof},{"performance_adoption_enabled",false}};
    J policy={{"native_model_free_speculation",scope},{"native_prefill",{{"tokens",4}}},
        {"native_padded_expert_cache",J::object()}};
    qwen_app::require_model_free_speculation_policy(policy);
    auto online=policy;online["native_model_free_speculation"]["verification_policy"]="expert-union-online-v1";
    refused([&]{qwen_app::require_model_free_speculation_policy(online);});
    online["native_expert_routes"]=J::object();qwen_app::require_model_free_speculation_policy(online);
    auto wrong_online=online;wrong_online["native_model_free_speculation"]["verification_policy"]="future-reference";
    refused([&]{qwen_app::require_model_free_speculation_policy(wrong_online);});
    for(auto it=scope.begin();it!=scope.end();++it){auto bad=policy;bad["native_model_free_speculation"].erase(it.key());
        refused([&]{qwen_app::require_model_free_speculation_policy(bad);});}
    for(auto it=proof.begin();it!=proof.end();++it){auto bad=policy;bad["native_model_free_speculation"]["complete_checkpoint_qualification"][it.key()]=nullptr;
        refused([&]{qwen_app::require_model_free_speculation_policy(bad);});}
    for(const auto key:{"native_large_cache_scope","native_prefix_validation","native_model_checkpoint_validation"}){
        auto bad=policy;bad[key]=J::object();refused([&]{qwen_app::require_model_free_speculation_policy(bad);});}
    for(const auto key:{"target_batch_tokens","maximum_attempts_per_process","maximum_generated_tokens_per_request","active_cache_slots"}){
        auto bad=policy;bad["native_model_free_speculation"][key]=999;
        refused([&]{qwen_app::require_model_free_speculation_policy(bad);});}
    auto bad=policy;bad["native_prefill"]["tokens"]=2;refused([&]{qwen_app::require_model_free_speculation_policy(bad);});
    J report={{"schema","ps5-qwen-model-checkpoint-validation-result-v1"},{"pid",123},{"run_id",run},
        {"captures",25},{"restores",25},{"prefill_replays",2},{"next_replays_including_EOG",23},
        {"original_route_rows_compared",1152},{"maximum_absolute_logit_error",0},
        {"all_original_expert_selections_exact",true},{"all_continuation_tokens_and_bytes_exact",true},
        {"device_ledger_live_bytes",0},{"all_model_source_and_checkpoint_owners_retired",true}};
    qwen_app::require_model_free_checkpoint_report(report,proof);
    for(auto it=report.begin();it!=report.end();++it){auto changed=report;changed.erase(it.key());
        refused([&]{qwen_app::require_model_free_checkpoint_report(changed,proof);});}
    std::cout<<failures<<" causal scope and native prerequisite refusals passed\n";
}
