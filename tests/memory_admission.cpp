// SPDX-License-Identifier: MIT
#include "memory_admission.h"
#include <iostream>
#include <stdexcept>
using namespace qwen_app;
static void check(bool value){if(!value)throw std::runtime_error("Memory admission check failed");}
template<class Function>void reject(Function run){bool failed=false;try{run();}catch(const std::exception &){failed=true;}check(failed);}
int main(){
    try{
        ModelFootprint model;model.trunk_layers=48;model.mapped_files=360ull<<30;
        model.tensor("token_embd.weight",1ull<<30);model.tensor("per_layer_token_embd.weight",100ull<<30);
        model.tensor("blk.0.ffn_up_exps.weight",200ull<<30);model.tensor("blk.0.attn_q.weight",1ull<<30);
        model.tensor("blk.48.nextn.eh_proj.weight",4ull<<30);
        check(model.device_weights==(1ull<<30)&&model.mapped_experts==(200ull<<30)&&model.lazy_ple==(100ull<<30));
        check(model.mapped_embeddings==(1ull<<30)&&model.skipped_mtp==(4ull<<30));
        MemoryBudget budget;MemoryObservation observed{16ull<<30,16ull<<30,4ull<<30,2ull<<30};budget.admit(model,observed);
        auto limited=observed;limited.os_free=0;reject([&]{budget.admit(model,limited);});
        limited=observed;limited.driver_free=budget.device_requirement(model)-1;reject([&]{budget.admit(model,limited);});
        limited=observed;limited.direct_largest=budget.device_requirement(model)-1;reject([&]{budget.admit(model,limited);});
        limited=observed;limited.os_free=budget.cpu_working+budget.os_reserve-1;reject([&]{budget.admit(model,limited);});
        limited=observed;limited.device_max_buffer=(1ull<<30)-1;reject([&]{budget.admit(model,limited);});
        auto incomplete=model;incomplete.lazy_ple=0;reject([&]{budget.admit(incomplete,observed);});
        incomplete=model;incomplete.mapped_files=513ull<<30;reject([&]{budget.admit(incomplete,observed);});
        reject([]{checked_memory_sum(UINT64_MAX,1);});
        std::cout<<"Tensor placement, PLE retention, UMA/Direct/OS admission and overflow rejection passed; host fixtures only\n";
    }catch(const std::exception & error){std::cerr<<error.what()<<'\n';return 1;}
}
