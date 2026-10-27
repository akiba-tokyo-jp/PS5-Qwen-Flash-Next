// SPDX-License-Identifier: MIT
#include "resident_additional_policy.h"
#include <fstream>
#include <iostream>
using J=nlohmann::json;
int main(int argc,char **argv) {
    if(argc!=2)return 2;std::ifstream input(argv[1]);J original;input>>original;unsigned refused=0;
    for(const std::string kind:{"cache","prefix"})for(const unsigned slots:{53u,128u}) {
        if(kind=="prefix"&&slots==128)continue;
        auto p=original;p["native_resident_comparison"]=qwen_app::resident_additional_scope(kind,slots);
        p["native_padded_expert_cache"]["active_slots"]=slots;
        p["native_padded_expert_cache"]["cache_cap_bytes"]=slots==53?536870912ull:1274462208ull;
        if(slots==128)p["native_large_cache_scope"]={{"stage","model"}};
        qwen_app::require_resident_additional_policy(p,kind);
        const auto reject=[&](const J &v){bool failed=false;
            try{qwen_app::require_resident_additional_policy(v,kind);}catch(const std::exception &){failed=true;}
            if(!failed)throw std::runtime_error("Invalid additional comparison admitted");++refused;};
        for(const auto *key:{"maximum_requests","warmup_requests","matched_groups","requests_per_group",
            "forced_rejection_requests","context_tokens","prefill_tokens","active_cache_slots",
            "maximum_output_tokens","model_loads","HTTP_requests","VideoOut_starts","automatic_retries"}) {
            auto a=p;a["native_resident_comparison"][key]=a["native_resident_comparison"][key].get<int>()+1;reject(a);
            a=p;a["native_resident_comparison"][key]=double(a["native_resident_comparison"][key].get<int>());reject(a);
        }
        for(const auto *key:{"enabled","CPU_startup_calibration","CPU_preparation_uses_operational_floor",
            "legacy_transport_scope_overridden","all_original_precision_preserved","performance_adoption_enabled"}) {
            auto a=p;a["native_resident_comparison"][key]=!a["native_resident_comparison"][key].get<bool>();reject(a);}
        for(const auto *key:{"native_predictive_cache","native_model_free_speculation","native_prefix_validation",
            "native_resident_GPU_capacity_only"}){auto a=p;a[key]=true;reject(a);}
        auto a=p;a["native_resident_comparison"]["extra"]=true;reject(a);
        a=p;a["native_padded_expert_cache"]["cache_cap_bytes"]=1;reject(a);
        a=p;a["deployment_enabled"]=true;reject(a);
        a=p;if(slots==128)a.erase("native_large_cache_scope");else a["native_large_cache_scope"]={};reject(a);
    }
    std::cout<<"{\"valid_scopes\":3,\"refusals\":"<<refused<<"}\n";
}
