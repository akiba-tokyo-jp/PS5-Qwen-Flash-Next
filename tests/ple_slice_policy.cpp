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
    auto smoke=valid;
    auto &scope=smoke["native_PLE_slice_validation"];
    scope["schema"]="ps5-qwen-PLE-slice-smoke-policy-v1";scope["rounds"]=0u;scope["maximum_graphs"]=4u;scope["widths"]={1u};
    auto &storage=smoke["native_shader_storage"];storage["verify_all_original_assets_before_Vulkan"]=false;
    const std::string h(64,'0'),run(32,'0');
    storage["prior_native_CPU"]={{"report_path","/app0/qwen-runtime/plan-"+run+".json.shader-assets.CPU"},
        {"report_bytes",1024u},{"report_sha256",h},{"pid",1u},{"run_id",run},{"prior_SELF_sha256",h},{"resource_manifest_sha256",h},
        {"all_original_assets_completed_on_this_boot",true},{"same_encoded_resources_and_per_use_decoder_in_current_SELF",true},
        {"current_module_input_full_SHA256_required",true}};
    qwen_app::require_native_validation_policy(smoke,"PLE-slice-validation",false);
    const auto reject_smoke=[&](const std::function<void(nlohmann::json&)> &edit){auto p=smoke;edit(p);try{qwen_app::require_native_validation_policy(p,"PLE-slice-validation",false);return false;}catch(...){++refused;return true;}};
    for(const auto *name:{"rounds","maximum_graphs","widths","schema"})
        if(!reject_smoke([&](auto &p){p["native_PLE_slice_validation"][name]=valid.at("native_PLE_slice_validation").at(name);}))return 13;
    for(const auto &item:storage.at("prior_native_CPU").items())
        if(!reject_smoke([&](auto &p){p["native_shader_storage"]["prior_native_CPU"].erase(item.key());}))return 14;
    for(const auto *name:{"all_original_assets_completed_on_this_boot","same_encoded_resources_and_per_use_decoder_in_current_SELF","current_module_input_full_SHA256_required"})
        if(!reject_smoke([&](auto &p){p["native_shader_storage"]["prior_native_CPU"][name]=false;}))return 15;
    if(!reject_smoke([](auto &p){p["native_shader_storage"]["prior_native_CPU"]["report_bytes"]=4097u;})||
       !reject_smoke([](auto &p){p["native_shader_storage"]["verify_all_original_assets_before_Vulkan"]=true;})||
       !reject_smoke([](auto &p){p["native_shader_storage"]["prior_native_CPU"]["report_path"]="/data/unowned";}))return 16;
    auto v2=smoke;v2["native_PLE_slice_validation"]["schema"]="ps5-qwen-PLE-slice-smoke-policy-v2";
    v2["native_PLE_slice_validation"]["source_guard"]={{"schema","ps5-qwen-PLE-qualified-source-owner-v1"},
        {"path","/app0/qwen-runtime/vector-bank-0.pack"},{"bytes",63488000u},{"sha256",h},
        {"numerical_input",false},{"current_whole_native_integrity_required",true}};
    qwen_app::require_native_validation_policy(v2,"PLE-slice-validation",false);
    const auto reject_v2=[&](const std::function<void(nlohmann::json&)> &edit){auto p=v2;edit(p);try{qwen_app::require_native_validation_policy(p,"PLE-slice-validation",false);return false;}catch(...){++refused;return true;}};
    for(const auto &item:v2.at("native_PLE_slice_validation").at("source_guard").items())
        if(!reject_v2([&](auto &p){p["native_PLE_slice_validation"]["source_guard"].erase(item.key());}))return 17;
    if(!reject_v2([](auto &p){p["native_PLE_slice_validation"]["source_guard"]["path"]="/app0/qwen-runtime/development.json";})||
       !reject_v2([](auto &p){p["native_PLE_slice_validation"]["source_guard"]["bytes"]=1u;})||
       !reject_v2([](auto &p){p["native_PLE_slice_validation"]["source_guard"]["bytes"]=134217729u;})||
       !reject_v2([](auto &p){p["native_PLE_slice_validation"]["source_guard"]["bytes"]=63488000.0;})||
       !reject_v2([](auto &p){p["native_PLE_slice_validation"]["source_guard"]["sha256"]="bad";})||
       !reject_v2([](auto &p){p["native_PLE_slice_validation"]["source_guard"]["numerical_input"]=true;})||
       !reject_v2([](auto &p){p["native_PLE_slice_validation"]["source_guard"]["current_whole_native_integrity_required"]=false;})||
       !reject_v2([](auto &p){p["native_PLE_slice_validation"]["schema"]="ps5-qwen-PLE-slice-smoke-policy-v1";}))return 18;
    auto paired=v2;auto &paired_scope=paired["native_PLE_slice_validation"];
    paired_scope["schema"]="ps5-qwen-PLE-slice-paired-policy-v2";paired_scope["rounds"]=8u;
    paired_scope["maximum_graphs"]=208u;paired_scope["widths"]={1u,2u,3u,4u};
    qwen_app::require_native_validation_policy(paired,"PLE-slice-validation",false);
    std::array<std::uint64_t,10> identity{{1,2,0100644,0,0,63488000,0,0,0,0}};
    qwen_app::require_PLE_source_identity(identity,63488000);
    for(const auto &item:{std::pair<unsigned,std::uint64_t>{1,0},{2,0100666},{2,0100664},{2,0120777},{5,1}}) {
        auto changed=identity;changed[item.first]=item.second;
        try{qwen_app::require_PLE_source_identity(changed,63488000);return 19;}catch(...){++refused;}
    }
    std::cout<<"{\"headless_startup_and_policy_passed\":true,\"invalid_scope_refusals\":"<<refused<<",\"PS5_operations\":0}"<<std::endl;
}
