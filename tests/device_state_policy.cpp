// SPDX-License-Identifier: MIT
#include "device_state_admission.h"
#include "startup.h"
#include <fstream>
#include <functional>
#include <iostream>
int main(int argc,char **argv) {
    if(argc!=3)return 2;std::ifstream file(argv[1]);const auto source=nlohmann::json::parse(file);
    char *args[]={argv[0],argv[2]};const auto startup=qwen_app::read_startup(2,args);
    if(!startup.device_state_validation||startup.native_display||startup.vector_bank_validation||startup.palette_validation||startup.first_generation_validation||startup.clock_calibration)return 3;
    qwen_app::require_device_state_policy(source,false);unsigned refused=0;
    auto bad=[&](const std::function<void(nlohmann::json &)> &edit){auto copy=source;edit(copy);try{qwen_app::require_device_state_policy(copy,false);return false;}catch(...){++refused;return true;}};
    try{qwen_app::require_device_state_policy(source,true);return 4;}catch(...){++refused;}
    for(const auto *key:{"schema","enabled","driver_revision","profile","native_archive_sha256","model_loading_enabled","persistent_caches_enabled","state_bytes","maximum_GPU_memory_bytes","cases","source"})
        if(!bad([&](auto &p){p["native_device_state_validation"].erase(key);}))return 5;
    if(!bad([](auto &p){p["native_device_state_validation"]["model_loading_enabled"]=true;})||
       !bad([](auto &p){p["native_device_state_validation"]["persistent_caches_enabled"]=true;})||
       !bad([](auto &p){p["native_device_state_validation"]["cases"]=8.0;})||
       !bad([](auto &p){p["native_device_state_validation"]["state_bytes"]=142606336.0;})||
       !bad([](auto &p){p["native_device_state_validation"]["maximum_GPU_memory_bytes"]=536870912.0;})||
       !bad([](auto &p){p["native_device_state_validation"]["source"]["path"]="/data/unowned";})||
       !bad([](auto &p){p["native_device_state_validation"]["source"]["bytes"]=1u;})||
       !bad([](auto &p){p["native_device_state_validation"]["source"]["sha256"]=std::string(64,'0');})||
       !bad([](auto &p){p.erase("native_shader_storage");})||
       !bad([](auto &p){p["native_shader_storage"]["verify_all_original_assets_before_Vulkan"]=false;})||
       !bad([](auto &p){p["native_shader_storage"]["prior_native_CPU"]=nlohmann::json::object();}))return 6;
    std::cout<<"{\"valid_policy\":true,\"headless_startup_parsed\":true,\"invalid_policy_refusals\":"<<refused<<",\"PS5_operations\":0}"<<std::endl;
}
