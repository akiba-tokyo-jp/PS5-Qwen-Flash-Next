// SPDX-License-Identifier: MIT
#include "resident_combined_policy.h"
#include "resident_postloader_integrity.h"
#include <fstream>
#include <iostream>
using J=nlohmann::json;
int main(int argc,char **argv) {
    if(argc!=2)return 2;std::ifstream input(argv[1]);J p;input>>p;
    p["native_resident_comparison"]=qwen_app::resident_combined_scope();
    p["native_resident_postloader_integrity"]={{"schema","ps5-qwen-postloader-SELF-integrity-v1"},{"enabled",true},
        {"full_current_SELF_SHA256_required",true},{"maximum_read_window_bytes",1048576},
        {"additional_VM_pages",19},{"maximum_passes",1},{"GPU_before_completion",false},
        {"automatic_retries",0},{"cache_recovery_assumed_before_measurement",false}};
    const auto check=[](const J &v){qwen_app::require_resident_combined_policy(v);qwen_app::require_resident_postloader_integrity(v);};
    check(p);unsigned refused=0;
    const auto reject=[&](const J &v){bool failed=false;try{check(v);}catch(const std::exception &){failed=true;}
        if(!failed)throw std::runtime_error("Invalid combined/postloader policy admitted");++refused;};
    for(const auto *scope:{"native_resident_comparison","native_resident_postloader_integrity"})
        for(auto i=p[scope].begin();i!=p[scope].end();++i){
            auto a=p;a[scope].erase(i.key());reject(a);a=p;
            if(i.value().is_number_integer())a[scope][i.key()]=i.value().get<int>()+1;
            else if(i.value().is_boolean())a[scope][i.key()]=!i.value().get<bool>();
            else a[scope][i.key()]="wrong";
            reject(a);
            if(i.value().is_number_integer()){a=p;a[scope][i.key()]=double(i.value().get<int>());reject(a);}
        }
    for(const auto *key:{"native_large_cache_scope","native_predictive_cache","native_model_free_speculation"}){
        auto a=p;a[key]=true;reject(a);}
    auto a=p;a["native_resident_postloader_integrity"]["unexpected"]=true;reject(a);
    std::cout<<"{\"combined_and_postloader_passed\":true,\"invalid_controls_refused\":"<<refused<<"}\n";
}
