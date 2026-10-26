// SPDX-License-Identifier: MIT
#include "prefix_validation_policy.h"
#include <fstream>
#include <functional>
#include <iostream>
int main(int argc,char **argv) {
    if(argc!=2)return 2;std::ifstream file(argv[1]);const auto source=nlohmann::json::parse(file);
    qwen_app::require_prefix_validation_policy(source);auto control=source;control["native_prefix_validation"]["prefix_reuse_enabled"]=false;
    qwen_app::require_prefix_validation_policy(control);
    unsigned refused=0;
    const auto bad=[&](const std::function<void(nlohmann::json &)> &edit) {
        auto p=source;edit(p);try{qwen_app::require_prefix_validation_policy(p);return false;}catch(...){++refused;return true;}
    };
    for(auto it=source.at("native_prefix_validation").begin();it!=source.at("native_prefix_validation").end();++it)
        if(!bad([&](auto &p){p["native_prefix_validation"].erase(it.key());}))return 3;
    if(!bad([](auto &p){p["native_prefix_validation"]["prefix_reuse_enabled"]=1;})||
       !bad([](auto &p){p["native_prefix_validation"]["maximum_state_bytes"]=142606336.0;})||
       !bad([](auto &p){p["native_prefix_validation"]["maximum_additional_CPU_bytes"]=33554432u;})||
       !bad([](auto &p){p["native_prefix_validation"]["maximum_logit_records_per_request"]=34u;})||
       !bad([](auto &p){p["native_prefix_validation"]["full_F32_logit_fingerprints"]=false;})||
       !bad([](auto &p){p["native_prefix_validation"]["checkpoint_qualification_SELF_SHA256"]="changed";})||
       !bad([](auto &p){p["native_prefix_validation"]["checkpoint_qualification_result_SHA256"]="changed";})||
       !bad([](auto &p){p["native_model_checkpoint_validation"]=nlohmann::json::object();})||
       !bad([](auto &p){p["native_prefill"]["tokens"]=2u;})||
       !bad([](auto &p){p["native_expert_routes"]["enabled"]=false;})||
       !bad([](auto &p){p["native_expert_routes"]["additional_GPU_downloads"]=1u;}))return 4;
    std::cout<<"{\"policy_refusals\":"<<refused<<",\"both_prefix_switches_valid\":true,\"PS5_operations\":0}"<<std::endl;
}
