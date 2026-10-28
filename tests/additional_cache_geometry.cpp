// SPDX-License-Identifier: MIT
#include "padded_cache_geometry.h"
#include "padded_bank_layout.h"
#include <cassert>
int main(){
    using namespace qwen_app;
    assert(selected_padded_cache_geometry().active_slots==53);
    assert(PaddedCacheGeometry{128}.cache_bytes()==1274462208);
    assert(PaddedCacheGeometry{134}.cache_bytes()==1333739520);
    bool refused=false;try{request_additional_cache_slots(135);}catch(const std::invalid_argument&){refused=true;}assert(refused);
    request_additional_cache_slots(134);select_experimental_padded_cache_128();
    auto selected=selected_padded_cache_geometry();assert(selected.active_slots==134&&selected.physical_slots()==135);
    for(auto residue:original_bank_residues){
        auto first=selected.slot(0,residue,135*padded_bank_stride,32);
        auto last=selected.slot(133,residue,135*padded_bank_stride,32);
        assert(first.payload_offset==residue&&last.payload_offset==133*padded_bank_stride+residue);
        assert(last.requested_bytes<=135*padded_bank_stride-last.aligned_write_offset);
    }
    refused=false;try{selected.slot(134,0,135*padded_bank_stride,64);}catch(const std::invalid_argument&){refused=true;}assert(refused);
    refused=false;try{select_experimental_padded_cache_128();}catch(const std::logic_error&){refused=true;}assert(refused);
    assert(selected_padded_buffer_batch_limit(1ull<<30,true)==(512ull<<20));
}
