// SPDX-License-Identifier: MIT
#include "validation_policy.h"
#include "startup.h"
#include <fstream>
#include <functional>
#include <iostream>
int main(int argc,char **argv) {
    if(argc!=5)return 2;
    std::ifstream file(argv[1]);const auto valid=nlohmann::json::parse(file);unsigned refused=0;
    char *args[]={argv[0],argv[2]};const auto startup=qwen_app::read_startup(2,args);
    if(!startup.PLE_slice_validation||startup.native_display||startup.device_state_validation||startup.vector_bank_validation||
        startup.first_generation_validation||startup.clock_calibration)return 3;
    qwen_app::require_native_validation_policy(valid,"PLE-slice-validation",false);
    auto bad=[&](const std::function<void(nlohmann::json&)> &edit){auto p=valid;edit(p);try{qwen_app::require_native_validation_policy(p,"PLE-slice-validation",false);return false;}catch(...){++refused;return true;}};
    try{qwen_app::require_native_validation_policy(valid,"PLE-slice-validation",true);return 4;}catch(...){++refused;}
    for(const auto *key:{"schema","enabled","driver_revision","profile","native_archive_sha256","model_loading_enabled",
            "persistent_caches_enabled","deterministic_data","maximum_GPU_payload_bytes","rounds","maximum_graphs",
            "maximum_source_scratch_bytes","widths","modes"})if(!bad([&](auto &p){p["native_PLE_slice_validation"].erase(key);}))return 5;
    for(const auto *key:{"maximum_GPU_payload_bytes","rounds","maximum_graphs","maximum_source_scratch_bytes"})
        if(!bad([&](auto &p){p["native_PLE_slice_validation"][key]=p["native_PLE_slice_validation"][key].template get<double>();}))return 6;
    for(const auto *key:{"model_loading_enabled","persistent_caches_enabled"})if(!bad([&](auto &p){p["native_PLE_slice_validation"][key]=true;}))return 7;
    for(const auto *key:{"widths","modes"})for(unsigned i=0;i<4;++i)
        if(!bad([&](auto &p){p["native_PLE_slice_validation"][key][i]=1.0;}))return 8;
    for(const auto *key:{"driver_revision","profile","native_archive_sha256","deterministic_data"})
        if(!bad([&](auto &p){p["native_PLE_slice_validation"][key]="wrong";}))return 9;
    for(const auto *key:{"schema","enabled","verify_all_original_assets_before_Vulkan","model_and_shader_precision_unchanged","persistent_caches_enabled",
            "registry_sha256","shader_count","original_bytes","stored_bytes","lookup_entries","external_file"})
        if(!bad([&](auto &p){p["native_shader_storage"].erase(key);}))return 10;
    if(!bad([](auto &p){p["native_shader_storage"]["prior_native_CPU"]=nlohmann::json::object();})||
       !bad([](auto &p){p["native_shader_storage"]["verify_all_original_assets_before_Vulkan"]=false;})||
       !bad([](auto &p){p["native_shader_storage"]["external_file"]["path"]="/data/unowned";})||
       !bad([](auto &p){p["native_shader_storage"]["external_file"]["input_window_bytes"]=1u;})||
       !bad([](auto &p){p["native_shader_storage"]["external_file"]["bytes"]=2u;})||
       !bad([](auto &p){p["native_shader_storage"]["external_file"]["sha256"]="invalid";}))return 11;
    for(unsigned i=3;i<5;++i) {
        char *bad_args[]={argv[0],argv[i]};try{(void)qwen_app::read_startup(2,bad_args);return 12;}catch(...){++refused;}
    }
    std::cout<<"{\"headless_startup_and_policy_passed\":true,\"invalid_scope_refusals\":"<<refused<<",\"PS5_operations\":0}"<<std::endl;
}
