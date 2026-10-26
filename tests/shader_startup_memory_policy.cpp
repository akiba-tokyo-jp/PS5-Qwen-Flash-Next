// SPDX-License-Identifier: MIT
#include "shader_startup_memory_policy.h"
#include <iostream>
int main() {
    using Json=nlohmann::json;
    const Json diagnostic={{"schema","ps5-qwen-shader-startup-memory-v1"},{"enabled",true},{"CPU_only",true},
        {"maximum_stage_records",2048u},{"matched_idle_ns",2000000u},{"split_write_and_sync",true},
        {"stop_before_model_metadata",true},{"GPU_calls",0u},{"source_workers",0u},{"automatic_retries",0u}};
    const Json good={{"native_shader_startup_memory_diagnostic",diagnostic},{"native_first_generation_validation",Json::object()},
        {"native_boundary_memory_diagnostic",Json::object()},{"native_source_schedule",{{"startup_integrity_direct",true}}},
        {"native_shader_storage",{{"verify_all_original_assets_before_Vulkan",false},{"prior_native_CPU",Json::object()}}}};
    qwen_app::require_shader_startup_memory_policy(good);unsigned refusals=0;
    const auto bad=[&](const Json &p){try{qwen_app::require_shader_startup_memory_policy(p);}catch(...){++refusals;return;}throw std::runtime_error("Invalid shader attribution policy accepted");};
    for(auto it=diagnostic.begin();it!=diagnostic.end();++it){auto p=good;p["native_shader_startup_memory_diagnostic"].erase(it.key());bad(p);}
    for(const auto *key:{"CPU_only","split_write_and_sync","stop_before_model_metadata"}){auto p=good;p["native_shader_startup_memory_diagnostic"][key]=false;bad(p);}
    for(const auto *key:{"maximum_stage_records","matched_idle_ns","GPU_calls","source_workers","automatic_retries"}){
        auto p=good;p["native_shader_startup_memory_diagnostic"][key]=diagnostic[key].get<double>();bad(p);
        p=good;p["native_shader_startup_memory_diagnostic"][key]=diagnostic[key].get<unsigned>()+1u;bad(p);
    }
    for(const auto *key:{"native_prefix_validation","native_model_checkpoint_validation","native_metadata_memory_diagnostic",
            "native_source_stage_memory_diagnostic","native_SELF_read_control","native_report_CPU_diagnostic","native_frame_CPU_diagnostic"}){
        auto p=good;p[key]=Json::object();bad(p);
    }
    for(const auto *key:{"native_first_generation_validation","native_boundary_memory_diagnostic","native_source_schedule"}){auto p=good;p.erase(key);bad(p);}
    auto p=good;p["native_shader_storage"]["verify_all_original_assets_before_Vulkan"]=true;bad(p);
    p=good;p["native_shader_storage"].erase("prior_native_CPU");bad(p);
    std::cout<<Json({{"scope_refusals",refusals},{"GPU_execution",false}})<<std::endl;
}
