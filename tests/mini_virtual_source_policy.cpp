// SPDX-License-Identifier: MIT
#include "mini_virtual_source_policy.h"
#include <functional>
#include <iostream>
using J=nlohmann::json;
int main(){try{
    J p={{"console_operations_enabled",true},{"allowed_modes",J::array({"first-generation-validation"})},
        {"native_first_generation_validation",{{"run_id",std::string(32,'a')},{"candidate_SELF_sha256",std::string(64,'b')},
            {"candidate_SELF_bytes",123456u},{"model_receipt_sha256",std::string(64,'c')},{"model_receipt_bytes",95068u}}},
        {"native_completed_metadata",{{"run_id",std::string(32,'d')},{"pid",473},{"report_bytes",150000u},
            {"report_path","/app0/qwen-runtime/plan-"+std::string(32,'d')+".json.metadata-memory"},
            {"report_sha256",std::string(64,'e')},{"SELF_sha256","7757d6dd79bc406945ee8a9688f1ca4e9ead80adc7981f66f540f73dfde787f6"}}},
        {"native_mini_virtual_source",{{"schema","ps5-qwen-mini-virtual-source-v1"},{"CPU_only",true},
            {"maximum_SELF_bytes",4u<<20},{"maximum_CPU_heap_bytes",64u<<20},{"maximum_live_regions",8},
            {"maximum_virtual_bytes",32ull<<30},{"source_indices",J::array({7,8,9,10,11,12,13,14})},
            {"modes",J::array({"per_file","shared_arena","shared_arena","per_file"})},
            {"match_native_journal_marker_count",true},{"quiet_seconds_before_rounds",5},
            {"extra_kernel_pages_before_round",512},{"GPU_calls",0},{"model_loads",0},
            {"model_payload_reads",0},{"source_workers",0},{"automatic_retries",0}}}};
    const auto path="/app0/qwen-runtime/plan-"+std::string(32,'a')+".json";unsigned refusals=0;
    auto require=[&](bool v){if(!v)throw std::runtime_error("CPU virtual-source policy control failed");};
    auto reject=[&](const std::function<void()> &fn){bool caught=false;try{fn();}catch(const std::exception&){caught=true;}require(caught);++refusals;};
    require(qwen_app::require_mini_virtual_source_policy(p,true,false,path)==std::string(32,'a'));
    for(auto i=p.begin();i!=p.end();++i){auto b=p;b.erase(i.key());reject([&]{qwen_app::require_mini_virtual_source_policy(b,true,false,path);});}
    for(const auto group:{"native_first_generation_validation","native_completed_metadata","native_mini_virtual_source"})
        for(auto i=p[group].begin();i!=p[group].end();++i){auto b=p;b[group].erase(i.key());reject([&]{qwen_app::require_mini_virtual_source_policy(b,true,false,path);});}
    for(const auto key:{"native_large_cache_scope","native_cache_layout_phase_memory","native_shader_storage",
            "native_prefix_validation","native_model_checkpoint_validation","native_model_free_speculation"}){
        auto b=p;b[key]=J::object();reject([&]{qwen_app::require_mini_virtual_source_policy(b,true,false,path);});}
    reject([&]{qwen_app::require_mini_virtual_source_policy(p,false,false,path);});
    reject([&]{qwen_app::require_mini_virtual_source_policy(p,true,true,path);});
    reject([&]{qwen_app::require_mini_virtual_source_policy(p,true,false,path+".other");});
    auto b=p;b["native_completed_metadata"]["SELF_sha256"]=std::string(64,'0');reject([&]{qwen_app::require_mini_virtual_source_policy(b,true,false,path);});
    b=p;b["native_mini_virtual_source"]["maximum_virtual_bytes"]=384ull<<30;reject([&]{qwen_app::require_mini_virtual_source_policy(b,true,false,path);});
    b=p;b["native_mini_virtual_source"]["modes"]=J::array({"per_file","shared_arena"});reject([&]{qwen_app::require_mini_virtual_source_policy(b,true,false,path);});
    for(const auto seconds:{0,4,6,60}){b=p;b["native_mini_virtual_source"]["quiet_seconds_before_rounds"]=seconds;
        reject([&]{qwen_app::require_mini_virtual_source_policy(b,true,false,path);});}
    std::cout<<J({{"CPU_virtual_source_scope_refusals",refusals},{"PS5_operations",0}}).dump()<<'\n';
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
