// SPDX-License-Identifier: MIT
#include "predictive_cache_policy.h"
#include <iostream>
using J=nlohmann::json;
static unsigned refused=0;
static void reject(const J &p){try{qwen_app::require_predictive_cache_policy(p);}catch(const std::exception&){++refused;return;}
    throw std::runtime_error("Invalid predictive-cache scope admitted");}
int main(){
    J scope={{"schema","ps5-qwen-predictive-cache-v1"},{"enabled",true},
        {"active_cache_slots",53},{"maximum_predicted_experts",1},{"maximum_source_reads",1},
        {"original_expert_roles",3},{"forecast_contexts",512},{"forecast_targets",16},
        {"minimum_prior_observations",2},{"minimum_frequency_numerator",3},
        {"minimum_frequency_denominator",4},{"protect_current_route",true},
        {"actual_backing_lease_required",true},{"join_before_source_or_slot_mutation",true},
        {"wait_ms",10000},{"automatic_retries",0},{"performance_adoption_enabled",false}};
    J p={{"native_predictive_cache",scope},{"native_prefill",{{"tokens",4}}},{"native_padded_expert_cache",J::object()}};
    qwen_app::require_predictive_cache_policy(p);
    for(auto it=scope.begin();it!=scope.end();++it){auto bad=p;bad["native_predictive_cache"][it.key()]=nullptr;reject(bad);}
    for(const auto *conflict:{"native_large_cache_scope","native_model_free_speculation","native_model_checkpoint_validation","native_prefix_validation"}) {
        auto bad=p;bad[conflict]=J::object();reject(bad);
    }
    auto bad=p;bad.erase("native_padded_expert_cache");reject(bad);
    bad=p;bad["native_prefill"]["tokens"]=2;reject(bad);
    std::cout<<"{\"predictive_policy_refusals\":"<<refused<<",\"PS5_operations\":0}\n";
}
