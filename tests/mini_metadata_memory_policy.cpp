// SPDX-License-Identifier: MIT
#include "mini_metadata_memory_policy.h"
#include <functional>
#include <iostream>
using J=nlohmann::json;
int main(){try{
    J p={{"console_operations_enabled",true},{"allowed_modes",J::array({"first-generation-validation"})},
        {"native_metadata_source_seal",J::object()},
        {"native_first_generation_validation",{{"run_id",std::string(32,'a')},{"candidate_SELF_sha256",std::string(64,'b')},
            {"candidate_SELF_bytes",123456u},{"model_receipt_sha256",std::string(64,'c')},{"model_receipt_bytes",95068u}}},
        {"native_mini_metadata_memory",{{"schema","ps5-qwen-mini-metadata-memory-v1"},{"CPU_only",true},
            {"maximum_SELF_bytes",4u<<20},{"maximum_CPU_heap_bytes",64u<<20},{"original_containers",76},
            {"ordered_records",380},{"GPU_calls",0},{"source_workers",0},{"virtual_source_calls",0},
            {"model_loads",0},{"automatic_retries",0}}}};
    const auto path="/app0/qwen-runtime/plan-"+std::string(32,'a')+".json";
    unsigned controls=0;
    auto require=[&](bool v){if(!v)throw std::runtime_error("CPU metadata policy control failed");};
    auto rejected=[&](const std::function<void()> &fn){bool caught=false;try{fn();}catch(const std::exception&){caught=true;}require(caught);++controls;};
    require(qwen_app::require_mini_metadata_memory_policy(p,true,false,path)==std::string(32,'a'));
    for(auto i=p.begin();i!=p.end();++i){auto b=p;b.erase(i.key());rejected([&]{qwen_app::require_mini_metadata_memory_policy(b,true,false,path);});}
    for(const auto key:{"native_first_generation_validation","native_mini_metadata_memory"})
        for(auto i=p[key].begin();i!=p[key].end();++i){auto b=p;b[key].erase(i.key());rejected([&]{qwen_app::require_mini_metadata_memory_policy(b,true,false,path);});}
    for(const auto key:{"native_large_cache_scope","native_cache_layout_phase_memory","native_shader_storage",
            "native_prefix_validation","native_model_checkpoint_validation","native_model_free_speculation"}){
        auto b=p;b[key]=J::object();rejected([&]{qwen_app::require_mini_metadata_memory_policy(b,true,false,path);});}
    rejected([&]{qwen_app::require_mini_metadata_memory_policy(p,false,false,path);});
    rejected([&]{qwen_app::require_mini_metadata_memory_policy(p,true,true,path);});
    rejected([&]{qwen_app::require_mini_metadata_memory_policy(p,true,false,path+".other");});
    auto b=p;b["native_first_generation_validation"]["candidate_SELF_bytes"]=4u*1024*1024+1;
    rejected([&]{qwen_app::require_mini_metadata_memory_policy(b,true,false,path);});
    b=p;b["native_first_generation_validation"]["model_receipt_bytes"]=0;
    rejected([&]{qwen_app::require_mini_metadata_memory_policy(b,true,false,path);});
    b=p;b["native_mini_metadata_memory"]["GPU_calls"]=1;
    rejected([&]{qwen_app::require_mini_metadata_memory_policy(b,true,false,path);});
    b=p;b["native_mini_metadata_memory"]["maximum_CPU_heap_bytes"]=512u<<20;
    rejected([&]{qwen_app::require_mini_metadata_memory_policy(b,true,false,path);});
    std::cout<<J({{"CPU_metadata_scope_refusals",controls},{"PS5_operations",0}}).dump()<<'\n';
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
