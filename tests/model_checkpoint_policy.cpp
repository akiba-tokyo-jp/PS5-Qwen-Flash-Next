// SPDX-License-Identifier: MIT
#include "model_checkpoint_policy.h"
#include <fstream>
#include <functional>
#include <iostream>
int main(int argc,char **argv) {
    if(argc!=2)return 2;std::ifstream file(argv[1]);const auto source=nlohmann::json::parse(file);qwen_app::require_model_checkpoint_policy(source);
    unsigned refused=0;auto bad=[&](const std::function<void(nlohmann::json &)> &edit){auto p=source;edit(p);try{qwen_app::require_model_checkpoint_policy(p);return false;}catch(...){++refused;return true;}};
    for(auto it=source.at("native_model_checkpoint_validation").begin();it!=source.at("native_model_checkpoint_validation").end();++it)
        if(!bad([&](auto &p){p["native_model_checkpoint_validation"].erase(it.key());}))return 3;
    if(!bad([](auto &p){p["native_model_checkpoint_validation"]["maximum_state_bytes"]=142606336.0;})||
       !bad([](auto &p){p["native_model_checkpoint_validation"]["request_ordinal"]=1u;})||
       !bad([](auto &p){p["native_model_checkpoint_validation"]["maximum_captures"]=35u;})||
       !bad([](auto &p){p["native_model_checkpoint_validation"]["maximum_output_tokens"]=64u;})||
       !bad([](auto &p){p["native_model_checkpoint_validation"]["prefill_positions"]={7u,28u};})||
       !bad([](auto &p){p["native_model_checkpoint_validation"]["prefill_positions"]={4.0,28.0};})||
       !bad([](auto &p){p["native_model_checkpoint_validation"]["relative_logit_tolerance"]=1e-4;})||
       !bad([](auto &p){p["native_model_checkpoint_validation"]["performance_adoption_enabled"]=true;})||
       !bad([](auto &p){p["native_prefill"]["tokens"]=2u;})||
       !bad([](auto &p){p["native_expert_routes"]["enabled"]=false;})||
       !bad([](auto &p){p["native_expert_routes"]["maximum_records"]=9216u;}))return 4;
    std::cout<<"{\"policy_refusals\":"<<refused<<",\"valid_complete_checkpoint_policy\":true,\"PS5_operations\":0}"<<std::endl;
}
