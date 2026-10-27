// SPDX-License-Identifier: MIT
#include "split_bank_admission.h"
#include <iostream>
using Json=nlohmann::json;
int main() {
    const auto good=Json{{"console_operations_enabled",true},{"console_validation_enabled",true},
        {"allowed_modes",Json::array({"first-generation-validation"})},
        {"native_split_bank_validation",{{"schema","ps5-qwen-split-bank-policy-v1"},{"enabled",true},
            {"driver_revision","872cc1264ad8ba5d6b888b092968fa5858a38c58"},{"profile","cumulative-idle"},
            {"native_archive_sha256","b57fe26e969940d147be05c1ffae830503d4865877281dffe03af32328f49925"},
            {"model_loading_enabled",false},{"persistent_caches_enabled",false},
            {"source_pack",{{"path",qwen_app::split_bank_pack_path},{"bytes",qwen_app::split_bank_pack_bytes},{"sha256",qwen_app::split_bank_pack_sha256}}}}},
        {"native_isolated_split_bank_title",{{"schema","ps5-qwen-isolated-split-bank-title-v1"},
            {"model_loading_enabled",false},{"source_workers",0u},{"candidate_SELF_bytes",1u<<20},
            {"candidate_SELF_sha256",std::string(64,'a')},{"run_id",std::string(32,'b')}}},
        {"native_shader_storage",{{"persistent_caches_enabled",false},{"model_and_shader_precision_unchanged",true},
            {"verify_all_original_assets_before_Vulkan",false},{"prior_native_CPU",Json::object()}}}};
    qwen_app::require_split_bank_policy(good,true,false,false);unsigned refusals=0;
    const auto refuse=[&](const Json &p,bool mode=true,bool display=false,bool clock=false){
        try{qwen_app::require_split_bank_policy(p,mode,display,clock);}catch(const std::exception &){++refusals;return;}
        throw std::runtime_error("An altered split-bank scope was accepted");
    };
    refuse(good,false);refuse(good,true,true);refuse(good,true,false,true);
    // Omitted fields, extra fields, wrong precision/source/driver or title
    // identity must all return before any native allocation or source read.
    for(const char *name:{"console_operations_enabled","console_validation_enabled","allowed_modes", "native_split_bank_validation",
        "native_isolated_split_bank_title","native_shader_storage"}){auto p=good;p.erase(name);refuse(p);}
    for(const char *section:{"native_split_bank_validation","native_isolated_split_bank_title"}) {
        for(auto it=good.at(section).begin();it!=good.at(section).end();++it){auto p=good;p[section].erase(it.key());refuse(p);}
        auto p=good;p[section]["unexpected"]=true;refuse(p);
    }
    for(const char *section:{"native_split_bank_validation","native_isolated_split_bank_title","native_shader_storage"})
        for(auto it=good.at(section).begin();it!=good.at(section).end();++it)
            if(it->is_boolean()){auto p=good;p[section][it.key()]=!it->get<bool>();refuse(p);}
    for(const char *key:{"path","bytes","sha256"}){auto p=good;p["native_split_bank_validation"]["source_pack"][key]="altered";refuse(p);}
    for(const char *key:{"driver_revision","profile","native_archive_sha256"}){auto p=good;p["native_split_bank_validation"][key]="altered";refuse(p);}
    for(const auto &bytes:Json::array({0u,(32u<<20)+1u,-1,1.5,"1024"})) {
        auto p=good;p["native_isolated_split_bank_title"]["candidate_SELF_bytes"]=bytes;refuse(p);
    }
    for(const auto &value:Json::array({1u,-1,0.0,"0"})) {auto p=good;p["native_isolated_split_bank_title"]["source_workers"]=value;refuse(p);}
    for(const char *key:{"candidate_SELF_sha256","run_id"})for(const auto &value:Json::array({"",std::string(64,'G'),"../unbound",1u})) {
        auto p=good;p["native_isolated_split_bank_title"][key]=value;refuse(p);
    }
    for(const auto &mode:Json::array({Json::array({"inference"}),Json::array({"first-generation-validation","inference"})})) {
        auto p=good;p["allowed_modes"]=mode;refuse(p);
    }
    auto ready=good;ready["native_ready_expert_numerical"]={{"schema","ps5-qwen-ready-numerical-policy-v1"},{"enabled",true},
        {"unique_original_experts",2u},{"original_contributions",10u},{"cohort_runs",6u},{"source_IO_depth",1u},{"representative_speed_test",false}};
    refuse(ready);ready["native_isolated_split_bank_title"]["source_workers"]=1u;
    qwen_app::require_split_bank_policy(ready,true,false,false);
    for(auto it=ready.at("native_ready_expert_numerical").begin();it!=ready.at("native_ready_expert_numerical").end();++it) {
        auto p=ready;p["native_ready_expert_numerical"].erase(it.key());refuse(p);
        p=ready;p["native_ready_expert_numerical"][it.key()]=nullptr;refuse(p);
        if(it->is_number_unsigned())for(const auto &v:Json::array({true,double(it->get<unsigned>()),-1})) {
            p=ready;p["native_ready_expert_numerical"][it.key()]=v;refuse(p);
        }
    }
    {auto p=ready;p["native_ready_expert_numerical"]["extra"]=true;refuse(p);}
    auto original=ready;original["native_ready_expert_original"]={{"schema","ps5-qwen-ready-original-policy-v1"},{"enabled",true},
        {"same_title_numerical_gate_required",true},{"unique_original_experts",10u},{"source_IO_depth",2u},{"cohort_runs",6u},{"source_plan_sha256",std::string(64,'c')}};
    refuse(original);original["native_isolated_split_bank_title"]["source_workers"]=2u;qwen_app::require_split_bank_policy(original,true,false,false);
    {auto p=original;p.erase("native_ready_expert_numerical");refuse(p);}
    for(auto it=original.at("native_ready_expert_original").begin();it!=original.at("native_ready_expert_original").end();++it) {
        auto p=original;p["native_ready_expert_original"].erase(it.key());refuse(p);p=original;p["native_ready_expert_original"][it.key()]=nullptr;refuse(p);
        if(it->is_number_unsigned())for(const auto &v:Json::array({true,double(it->get<unsigned>()),-1})){p=original;p["native_ready_expert_original"][it.key()]=v;refuse(p);}
    }
    auto scoped=original;scoped["native_split_bank_phase_memory"]={{"schema","ps5-qwen-split-bank-phase-memory-v1"},{"enabled",true},
        {"GPU_extra_operational_pages",1024u},{"model_loads",0u},{"regular_model_startup_target_unchanged",true},{"operational_floor_unchanged",true}};
    qwen_app::require_split_bank_policy(scoped,true,false,false);
    for(auto it=scoped.at("native_split_bank_phase_memory").begin();it!=scoped.at("native_split_bank_phase_memory").end();++it) {
        auto p=scoped;p["native_split_bank_phase_memory"].erase(it.key());refuse(p);p=scoped;p["native_split_bank_phase_memory"][it.key()]=nullptr;refuse(p);
    }
    for(const auto &v:Json::array({0u,512u,1023u,1025u,1024.0,true,-1})) {auto p=scoped;p["native_split_bank_phase_memory"]["GPU_extra_operational_pages"]=v;refuse(p);}
    {auto p=scoped;p.erase("native_ready_expert_numerical");p.erase("native_ready_expert_original");p["native_isolated_split_bank_title"]["source_workers"]=0u;refuse(p);}
    qwen_app::SystemMemoryObservation memory{512u<<20,16384,138739,2178,898,2974,206};
    if(qwen_app::split_bank_GPU_requirement(scoped,memory)!=2178||qwen_app::split_bank_GPU_requirement(original,memory)!=2974)
        throw std::runtime_error("Scoped fixture and regular startup targets must remain distinct");
    memory.kernel_free=1153;try{(void)qwen_app::split_bank_GPU_requirement(scoped,memory);throw std::logic_error("Operational floor reduced");}
    catch(const qwen_app::KernelMemoryPressure &){++refusals;}
    std::cout<<Json{{"exact_scope_passed",true},{"refusal_controls",refusals},{"PS5_operations",0},{"GPU_calls",0}}.dump()<<'\n';
}
