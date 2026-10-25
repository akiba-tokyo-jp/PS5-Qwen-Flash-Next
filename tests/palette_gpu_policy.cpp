// SPDX-License-Identifier: MIT
#include "palette_gpu_policy.h"
#include "startup.h"
#include <cassert>
#include <fstream>
#include <functional>
#include <vector>
using Json=nlohmann::json;
using qwen_app::require_palette_gpu_policy;
int main(int argc,char **argv) {
    const std::string hash(64,'a');
    Json sample={{"raw",{{"offset",0u},{"bytes",3276800u},{"requested",3276800u},{"sha256",hash}}},
        {"encoded",{{"offset",3276800u},{"bytes",2400000u},{"requested",2408448u},{"sha256",hash}}}};
    Json samples=Json::array();for(unsigned i=0;i<9;++i){auto s=sample;s["raw"]["offset"]=i*(6u<<20);s["encoded"]["offset"]=i*(6u<<20)+3276800u;samples.push_back(s);}
    Json policy={{"native_palette_validation",{
        {"schema","ps5-qwen-exact-palette-GPU-v1"},{"enabled",true},
        {"driver_revision","872cc1264ad8ba5d6b888b092968fa5858a38c58"},{"profile","cumulative-idle"},
        {"native_archive_sha256","b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"},
        {"model_loading_enabled",false},{"persistent_caches_enabled",false},
        {"maximum_GPU_memory_bytes",16u<<20},{"rounds",6u},
        {"pack",{{"path","/app0/qwen-runtime/palette-samples.pack"},{"bytes",64u<<20},{"sha256",hash}}},
        {"samples",samples},{"shaders",{
            {"copy",{{"path","/app0/qwen-runtime/palette-copy.spv"},{"bytes",20u},{"sha256",hash}}},
            {"palette",{{"path","/app0/qwen-runtime/palette-palette.spv"},{"bytes",20u},{"sha256",hash}}}}}
    }}};
    require_palette_gpu_policy(policy,false);
    unsigned rejected=0;
    auto refusal=[&](Json p,bool display=false){bool failed=false;try{require_palette_gpu_policy(p,display);}catch(const std::exception &){failed=true;}assert(failed);++rejected;};
    refusal(policy,true);
    auto &p=policy["native_palette_validation"];
    for(const char *key:{"schema","enabled","driver_revision","profile","native_archive_sha256","model_loading_enabled","persistent_caches_enabled","maximum_GPU_memory_bytes","rounds","pack","samples","shaders"}) {
        auto changed=policy;changed["native_palette_validation"].erase(key);refusal(changed);
    }
    for(const auto &change:std::vector<std::pair<std::string,Json>>{{"enabled",1u},{"model_loading_enabled",true},{"persistent_caches_enabled",true},
        {"maximum_GPU_memory_bytes",32u<<20},{"maximum_GPU_memory_bytes",16777216.0},{"rounds",7u},{"profile","control"}}) {
        auto changed=policy;changed["native_palette_validation"][change.first]=change.second;refusal(changed);
    }
    for(const char *role:{"raw","encoded"})for(const auto &change:std::vector<std::pair<std::string,Json>>{
        {"offset",1u},{"offset",128u<<20},{"bytes",0u},{"bytes",8u<<20},{"bytes",3.0},{"requested",1u},{"sha256","short"}}) {
        auto changed=policy;changed["native_palette_validation"]["samples"][0][role][change.first]=change.second;refusal(changed);
    }
    auto changed=policy;changed["native_palette_validation"]["pack"]["path"]="/data/ai/moss-qwen-lossless-../outside";refusal(changed);
    changed=policy;changed["native_palette_validation"]["samples"].erase(0);refusal(changed);
    changed=policy;changed["native_palette_validation"]["shaders"]["copy"]["path"]="/app0/other.spv";refusal(changed);
    changed=policy;changed["native_palette_validation"]["shaders"]["palette"]["bytes"]=21u;refusal(changed);
    changed=policy;changed["native_palette_validation"]["samples"][1]=changed["native_palette_validation"]["samples"][0];refusal(changed);
    assert(p.size()==12&&rejected>=38);
    if(argc==3) {
        std::ifstream f(argv[1]);require_palette_gpu_policy(Json::parse(f),false);
        char *args[]={argv[0],argv[2]};const auto startup=qwen_app::read_startup(2,args);
        assert(startup.palette_validation&&!startup.native_display&&!startup.first_generation_validation&&
            !startup.monitor_validation&&!startup.memory_validation);
    }else assert(argc==1);
    return 0;
}
