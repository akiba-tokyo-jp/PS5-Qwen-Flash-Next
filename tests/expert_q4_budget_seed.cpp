// SPDX-License-Identifier: MIT
// Compile with the candidate's exact qualified VFS geometry header.
#include <padded_cache_geometry.h>
#include "expert_q4_geometry.h"
#include <cassert>
#include <iostream>
int main(){
    qwen_app::request_additional_cache_slots(134);
    assert(qwen_app::additional_cache_slots()==134);
    qwen_app::select_experimental_padded_cache_128();
    const auto geometry=qwen_app::selected_padded_cache_geometry();
    assert(geometry.active_slots==134&&geometry.cache_bytes()==1333739520);
    const qwen_app::ExpertQ4Geometry q4{2560,640};
    assert(q4.maximum_contiguous_slots(geometry.cache_bytes(),256)==481);
    std::cout<<"{\"explicit_budget_seed_passed\":true,\"cache_budget_bytes\":1333739520,\"Q4_slots\":481}\n";
}
