// SPDX-License-Identifier: MIT
#include "mini_shader_bootstrap_policy.h"
#include <iostream>
using J=nlohmann::json;
static unsigned refusals=0;
template<class F>static void reject(F action){bool bad=false;try{action();}catch(const std::exception&){bad=true;}
    if(!bad)throw std::runtime_error("Invalid CPU bootstrap scope admitted");++refusals;}
int main(){
    const std::string run(32,'a'),path="/app0/qwen-runtime/plan-"+run+".json";
    J scope={{"schema","ps5-qwen-mini-shader-bootstrap-v1"},{"CPU_only",true},
        {"maximum_SELF_bytes",4u<<20},{"maximum_CPU_heap_bytes",16u<<20},{"complete_original_assets",1527},
        {"complete_original_lookups",382},{"GPU_calls",0},{"model_loads",0},{"source_workers",0},{"automatic_retries",0}};
    J binding={{"run_id",run},{"candidate_SELF_bytes",1200000u},{"candidate_SELF_sha256",std::string(64,'b')},
        {"model_receipt_bytes",200000u},{"model_receipt_sha256",std::string(64,'c')}};
    J policy={{"console_operations_enabled",true},{"allowed_modes",J::array({"first-generation-validation"})},
        {"native_mini_shader_bootstrap",scope},{"native_first_generation_validation",binding},
        {"native_shader_storage",{{"verify_all_original_assets_before_Vulkan",true}}}};
    const auto admit=[&](const J &p){return qwen_app::require_mini_shader_bootstrap_policy(p,true,false,path);};
    if(admit(policy)!=run)return 1;
    reject([&]{qwen_app::require_mini_shader_bootstrap_policy(policy,false,false,path);});
    reject([&]{qwen_app::require_mini_shader_bootstrap_policy(policy,true,true,path);});
    reject([&]{qwen_app::require_mini_shader_bootstrap_policy(policy,true,false,path+".other");});
    for(auto it=scope.begin();it!=scope.end();++it){auto bad=policy;bad["native_mini_shader_bootstrap"].erase(it.key());reject([&]{admit(bad);});}
    for(auto it=binding.begin();it!=binding.end();++it){auto bad=policy;bad["native_first_generation_validation"][it.key()]=nullptr;reject([&]{admit(bad);});}
    for(const auto key:{"native_mini_shader_title","native_shader_startup_memory_diagnostic"}){auto bad=policy;bad[key]=J::object();reject([&]{admit(bad);});}
    for(const auto key:{"GPU_calls","model_loads","source_workers","automatic_retries"}){auto bad=policy;bad["native_mini_shader_bootstrap"][key]=1;reject([&]{admit(bad);});}
    auto bad=policy;bad["native_shader_storage"]["prior_native_CPU"]=J::object();reject([&]{admit(bad);});
    bad=policy;bad["native_shader_storage"]["verify_all_original_assets_before_Vulkan"]=false;reject([&]{admit(bad);});
    bad=policy;bad["allowed_modes"].push_back("inference");reject([&]{admit(bad);});
    bad=policy;bad["native_first_generation_validation"]["candidate_SELF_bytes"]=5u<<20;reject([&]{admit(bad);});
    std::cout<<"{\"CPU_bootstrap_scope_refusals\":"<<refusals<<",\"PS5_operations\":0}\n";
}
