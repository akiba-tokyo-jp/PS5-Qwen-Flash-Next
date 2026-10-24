// SPDX-License-Identifier: MIT
// Exercise the actual native evidence validator without loading shader bytes.
#include "shader_assets.h"
#include "nlohmann/json.hpp"
#include <iostream>
#include <stdexcept>
using Json=nlohmann::json;
#include "actual_prior_shader_validator.h"
static unsigned exercise(const Json &good,const Json &prior,const qwen_app::ShaderAssetStats &assets) {
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
    return rejected;
}
int main(){try{
    qwen_app::ShaderAssetStats assets;assets.assets=1527;assets.lookup_entries=382;
    assets.original_bytes=38712204;assets.stored_bytes=10322484;assets.registry_sha256=std::string(64,'a');
    const Json prior={{"all_original_assets_completed_on_this_boot",true},
        {"same_encoded_resources_and_per_use_decoder_in_current_SELF",true},{"current_module_input_full_SHA256_required",true},
        {"pid",123},{"run_id",std::string(32,'b')}};
    Json good={{"schema","ps5-qwen-shader-storage-CPU-result-v1"},{"pid",123},{"run_id",std::string(32,'b')},
        {"GPU_calls",0},{"Vulkan_initialized",false},{"model_loaded",false},{"active_lease",false},{"failed",false},
        {"persistent_caches_enabled",false},{"all_original_SPIRV_bytes_preserved",true},
        {"shader_count",1527},{"CPU_verified_assets",1527},{"lookup_entries",382},{"CPU_verified_lookups",382},
        {"original_bytes",38712204},{"stored_bytes",10322484},{"registry_sha256",std::string(64,'a')}};
    unsigned rejected=exercise(good,prior,assets);
    assets.initialized=true;assets.external_file.registered=true;assets.external_file.verified=true;
    assets.external_file.file_bytes=8258588;assets.external_file.input_window_bytes=49152;assets.stored_bytes=8258588;
    good["schema"]="ps5-qwen-shader-storage-CPU-result-v3";good["stored_bytes"]=8258588;
    good.update(Json{{"all_assets_verified_in_this_run",true},{"prior_CPU_verified_assets",0},{"verification_mode","all_assets_in_current_run"},
        {"external_file",true},{"external_file_SHA256_verified",true},{"external_read_pending",false},{"external_source_failed",false},
        {"external_file_bytes",8258588},{"codec_input_window_bytes",49152},{"external_frame_requests",1527}});
    rejected+=exercise(good,prior,assets);
    for(unsigned mode=0;mode<7;++mode) {
        auto bad=assets;
        if(mode==0)bad.initialized=false;if(mode==1)bad.external_file.verified=false;
        if(mode==2)bad.external_file.failed=true;if(mode==3)bad.external_file.read_pending=true;
        if(mode==4)bad.external_file.frame_requests=1;if(mode==5)++bad.external_file.file_bytes;
        if(mode==6)++bad.external_file.input_window_bytes;
        bool refused=false;try{validate_prior_shader_CPU(good,prior,bad);}catch(...){refused=true;}
        if(!refused)throw std::runtime_error("Unqualified current external file accepted prior shader evidence");++rejected;
    }
    std::cout<<"Actual legacy/external native prior evidence validators: positive and "<<rejected<<" refusal controls passed\n";
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
