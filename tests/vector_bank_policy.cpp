// SPDX-License-Identifier: MIT
#include "vector_bank_admission.h"
#include "startup.h"
#include <fstream>
#include <iostream>
#include <functional>
int main(int argc,char **argv) {
    if(argc!=3)return 2;std::ifstream file(argv[1]);const auto source=nlohmann::json::parse(file);
    char *startup_args[]={argv[0],argv[2]};const auto startup=qwen_app::read_startup(2,startup_args);
    if(!startup.vector_bank_validation||startup.native_display||startup.palette_validation||startup.first_generation_validation||startup.clock_calibration)return 6;
    qwen_app::require_vector_bank_policy(source,false);unsigned refused=0;
    const auto bad=[&](const std::function<void(nlohmann::json &)> &edit) {
        auto copy=source;edit(copy);try{qwen_app::require_vector_bank_policy(copy,false);return false;}catch(...){++refused;return true;}
    };
    try{qwen_app::require_vector_bank_policy(source,true);return 3;}catch(...){++refused;}
    const bool compact=source.at("native_vector_bank_validation").at("schema")=="ps5-qwen-vector-bank-compact-v2";
    if(compact&&(!bad([](auto &v){v["native_vector_bank_validation"].erase("journal_style");})||
       !bad([](auto &v){v["native_vector_bank_validation"]["journal_style"]="per-call";})||
       !bad([](auto &v){v["native_vector_bank_validation"]["schema"]="ps5-qwen-vector-bank-v1";})))return 8;
    const char *keys[]={"enabled","driver_revision","profile","native_archive_sha256","model_loading_enabled","persistent_caches_enabled","maximum_GPU_memory_bytes","rounds","packs","groups"};
    for(auto key:keys)if(!bad([&](auto &v){v["native_vector_bank_validation"].erase(key);}))return 4;
    if(!bad([](auto &v){v["native_vector_bank_validation"]["model_loading_enabled"]=true;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["rounds"]=8.0;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["maximum_GPU_memory_bytes"]=536870912.0;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["groups"][0]["pack"]=0.0;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["persistent_caches_enabled"]=true;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["packs"][0]["bytes"]=1u;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["packs"][0]["path"]="/data/unowned";})||
       !bad([](auto &v){v["native_vector_bank_validation"]["groups"][0]["matrices"][1]["offset"]=1u;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["groups"][0]["matrices"][1]["residue"]=16000u;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["groups"][0]["matrices"][2]["offset"]=0u;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["groups"][3]["matrices"][0]["raw_sha256"]="bad";})||
       !bad([](auto &v){v["native_vector_bank_validation"]["groups"][3]["matrices"][1]["raw_sha256"]=std::string(64,'0');})||
       !bad([](auto &v){v["native_vector_bank_validation"]["groups"][3]["matrices"][0]["residue"]=0u;})||
       !bad([](auto &v){v["native_vector_bank_validation"]["groups"][4]=v["native_vector_bank_validation"]["groups"][3];}))return 5;
    if(!bad([](auto &v){v.erase("native_shader_storage");})||
       !bad([](auto &v){v["native_shader_storage"]["verify_all_original_assets_before_Vulkan"]=false;})||
       !bad([](auto &v){v["native_shader_storage"]["prior_native_CPU"]=nlohmann::json::object();})||
       !bad([](auto &v){v["native_shader_storage"]["shader_count"]=-1;})||
       !bad([](auto &v){v["native_shader_storage"]["shader_count"]=1.5;})||
       !bad([](auto &v){v["native_shader_storage"]["external_file"]["path"]="/data/unowned";})||
       !bad([](auto &v){v["native_shader_storage"]["registry_sha256"]="bad";})||
       !bad([](auto &v){v["native_shader_storage"]["external_file"]["input_window_bytes"]=1u;})||
       !bad([](auto &v){v["native_shader_storage"]["stored_bytes"]=0u;}))return 7;
    std::cout<<"{\"valid_policy\":true,\"headless_startup_parsed\":true,\"invalid_policy_refusals\":"<<refused<<",\"console_calls\":0}"<<std::endl;
}
