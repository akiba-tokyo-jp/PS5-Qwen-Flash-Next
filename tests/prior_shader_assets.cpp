// SPDX-License-Identifier: MIT
// Exercise the actual native evidence validator without loading shader bytes.
#include "shader_assets.h"
#include "nlohmann/json.hpp"
#include <iostream>
#include <stdexcept>
using Json=nlohmann::json;
#include "actual_prior_shader_validator.h"
int main(){try{
    qwen_app::ShaderAssetStats assets;assets.assets=1527;assets.lookup_entries=382;
    assets.original_bytes=38712204;assets.stored_bytes=10322484;assets.registry_sha256=std::string(64,'a');
    const Json prior={{"all_original_assets_completed_on_this_boot",true},
        {"same_encoded_resources_and_per_use_decoder_in_current_SELF",true},{"current_module_input_full_SHA256_required",true},
        {"pid",123},{"run_id",std::string(32,'b')}};
    const Json good={{"schema","ps5-qwen-shader-storage-CPU-result-v1"},{"pid",123},{"run_id",std::string(32,'b')},
        {"GPU_calls",0},{"Vulkan_initialized",false},{"model_loaded",false},{"active_lease",false},{"failed",false},
        {"persistent_caches_enabled",false},{"all_original_SPIRV_bytes_preserved",true},
        {"shader_count",1527},{"CPU_verified_assets",1527},{"lookup_entries",382},{"CPU_verified_lookups",382},
        {"original_bytes",38712204},{"stored_bytes",10322484},{"registry_sha256",std::string(64,'a')}};
    validate_prior_shader_CPU(good,prior,assets);unsigned rejected=0;
    for(const auto *key:{"all_original_assets_completed_on_this_boot","same_encoded_resources_and_per_use_decoder_in_current_SELF",
                        "current_module_input_full_SHA256_required"}) {
        auto bad=prior;bad[key]=false;bool refused=false;
        try{validate_prior_shader_CPU(good,bad,assets);}catch(...){refused=true;}
        if(!refused)throw std::runtime_error("An incomplete prior attestation was accepted");++rejected;
    }
    for(auto it=good.begin();it!=good.end();++it) {
        auto bad=good;
        if(it.value().is_boolean())bad[it.key()]=!it.value().get<bool>();
        else if(it.value().is_number())bad[it.key()]=it.value().get<std::uint64_t>()+1;
        else bad[it.key()]=it.value().get<std::string>()+"changed";
        bool refused=false;try{validate_prior_shader_CPU(bad,prior,assets);}catch(...){refused=true;}
        if(!refused)throw std::runtime_error("Changed original shader evidence was accepted");++rejected;
        bad=good;bad.erase(it.key());refused=false;
        try{validate_prior_shader_CPU(bad,prior,assets);}catch(...){refused=true;}
        if(!refused)throw std::runtime_error("Missing original shader evidence was accepted");++rejected;
    }
    std::cout<<"Actual native prior evidence validator: positive and "<<rejected<<" refusal controls passed\n";
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
