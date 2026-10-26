// SPDX-License-Identifier: MIT
// Metadata API stubs for the actual shared CPU shader-admission orchestration.
#include "shader_assets.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <unistd.h>
using Json=nlohmann::json;
namespace {
Json selected,report;std::string fault;
qwen_app::ShaderAssetStats assets;qwen_app::NativeShaderFileStats file_stats;
std::vector<std::string> calls;
void require(bool ok){if(!ok)throw std::runtime_error("Shader startup metadata control failed");}
}
namespace qwen_app {
bool native_shader_assets_registered(){return fault!="missing_registry";}
bool native_shader_file_registered(){return true;}
void initialize_native_shader_file(const std::string &path,std::uint64_t bytes,const std::string &digest) {
    require(path==selected["native_shader_storage"]["external_file"]["path"]&&digest==selected["native_shader_storage"]["external_file"]["sha256"]);
    calls.push_back("file");file_stats.registered=true;file_stats.verified=fault!="unverified_file";
    file_stats.read_pending=fault=="pending_read";file_stats.file_bytes=bytes;
    file_stats.input_window_bytes=selected["native_shader_storage"]["external_file"]["input_window_bytes"];
}
NativeShaderFileStats native_shader_file_stats(){return file_stats;}
void initialize_native_shader_assets() {
    calls.push_back("assets");const auto &p=selected["native_shader_storage"];
    assets.initialized=true;assets.assets=p["shader_count"];assets.original_bytes=p["original_bytes"];
    assets.stored_bytes=p["stored_bytes"];assets.lookup_entries=p["lookup_entries"];assets.CPU_verified_lookups=assets.lookup_entries;
    assets.registry_sha256=fault=="wrong_registry"?std::string(64,'0'):p["registry_sha256"].get<std::string>();
}
ShaderAssetStats native_shader_asset_stats(){assets.external_file=file_stats;return assets;}
ShaderAssetStats verify_native_shader_assets_CPU() {
    calls.push_back("verify");assets.CPU_verified_assets=assets.assets;file_stats.frame_requests=assets.assets;
    assets.active_lease=fault=="active_lease";assets.failed=fault=="failed_codec";
    return native_shader_asset_stats();
}
}
static void require_model_CPU_budget(){calls.push_back("heap");if(fault=="heap")throw std::runtime_error("Host heap refusal");}
static void write_fresh_report(const std::string &,const Json &value){calls.push_back("report");report=value;}
static Json read_prior_shader_CPU(const Json &,const qwen_app::ShaderAssetStats &a){return {{"CPU_verified_assets",a.assets}};}
extern "C" void qwen_native_stage(const char *){calls.push_back("stage");}

#include "actual_shader_CPU_admission.inc"

int main(int argc,char **argv) {
    if(argc!=2)return 2;std::ifstream input(argv[1]);selected=Json::parse(input);unsigned refused=0;
    admit_shader_storage_CPU(selected,"fixture",true,"host-fixture");
    require(report.at("all_assets_verified_in_this_run")==true&&report.at("CPU_verified_assets")==1527u&&
        report.at("GPU_calls")==0u&&report.at("Vulkan_initialized")==false&&report.at("run_id")=="host-fixture");
    require(calls==std::vector<std::string>{"file","stage","assets","verify","heap","report","stage"});
    for(const auto *failure:{"missing_registry","unverified_file","pending_read","wrong_registry","active_lease","failed_codec","heap"}) {
        fault=failure;calls.clear();report=Json();assets={};file_stats={};
        bool threw=false;try{admit_shader_storage_CPU(selected,"fixture",true,"host-fixture");}catch(...){threw=true;}
        require(threw&&report.is_null());++refused;
    }
    fault.clear();report=Json();assets={};file_stats={};
    try{admit_shader_storage_CPU(selected,"fixture",false,"host-fixture");return 3;}catch(...){++refused;}
    auto missing=selected;missing.erase("native_shader_storage");
    try{admit_shader_storage_CPU(missing,"fixture",true,"host-fixture");return 4;}catch(...){++refused;}
    std::cout<<Json({{"actual_shared_CPU_helper_extracted",true},{"successful_call_order_checked",true},
        {"known_CPU_refusals",refused},{"host_metadata_stubs",true},{"GPU_calls",0},{"model_inference",false}})<<std::endl;
}
