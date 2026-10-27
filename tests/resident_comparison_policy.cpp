// SPDX-License-Identifier: MIT
#include "resident_comparison_policy.h"
#include <fstream>
#include <iostream>
using J=nlohmann::json;
int main(int argc,char **argv){
    if(argc!=2)return 2;std::ifstream input(argv[1]);J p;input>>p;
    qwen_app::require_resident_comparison_policy(p);unsigned refused=0;
    const auto reject=[&](J value){bool failed=false;
        try{qwen_app::require_resident_comparison_policy(value);}catch(const std::exception &){failed=true;}
        if(!failed)throw std::runtime_error("An invalid resident scope was admitted");++refused;
    };
    for(const auto *key:{"maximum_requests","warmup_requests","matched_arms_per_candidate",
        "forced_rejection_requests","context_tokens","prefill_tokens","active_cache_slots",
        "maximum_output_tokens","model_loads","HTTP_requests","VideoOut_starts","automatic_retries","GPU_start_reference_pages"}){
        auto a=p;a["native_resident_comparison"][key]=a["native_resident_comparison"][key].get<int>()+1;reject(a);
        a=p;a["native_resident_comparison"][key]=double(a["native_resident_comparison"][key].get<int>());reject(a);
    }
    for(const auto *key:{"enabled","legacy_transport_scope_overridden","all_original_precision_preserved","performance_adoption_enabled",
        "CPU_startup_calibration","CPU_preparation_uses_operational_floor"}){
        auto a=p;a["native_resident_comparison"][key]=!a["native_resident_comparison"][key].get<bool>();reject(a);
    }
    for(const auto *key:{"native_predictive_cache","native_model_free_speculation","native_large_cache_scope",
        "native_direct_frame_evidence","native_cache_layout_phase_memory"}){auto a=p;a[key]=J::object();reject(a);}
    auto a=p;a["deployment_enabled"]=true;reject(a);
    a=p;a["allowed_modes"]=J::array({"inference"});reject(a);
    a=p;a["native_padded_expert_cache"]["active_slots"]=128;reject(a);
    a=p;a.erase("native_source_schedule");reject(a);
    a=p;a["native_resident_comparison"]["unknown"]=true;reject(a);
    auto cpu=p;cpu["native_resident_comparison"]=qwen_app::resident_comparison_scope(true);
    qwen_app::require_resident_comparison_policy(cpu);
    a=cpu;a["native_resident_comparison"]["maximum_requests"]=1;reject(a);
    a=cpu;a["native_resident_comparison"]["model_loads"]=1;reject(a);
    a=cpu;a["native_resident_comparison"]["CPU_startup_calibration"]=false;reject(a);
    a=cpu;a["native_resident_comparison"]["CPU_startup_calibration"]=1;reject(a);
    std::cout<<"{\"valid_model_and_CPU_scopes\":true,\"refusals\":"<<refused<<"}\n";
}
