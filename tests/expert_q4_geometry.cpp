// SPDX-License-Identifier: MIT
#include "expert_q4_geometry.h"
#include <cassert>
#include <iostream>
int main(){
    const qwen_app::ExpertQ4Geometry gate{2560,640},down{640,2560};
    assert(gate.payload_bytes()==921600&&down.payload_bytes()==921600);
    assert(gate.padded_stride()==1032192&&gate.padded_stride()%18==0&&gate.padded_stride()%16384==0);
    const auto slots=gate.maximum_contiguous_slots(1333739520,256);
    assert(slots==481&&3*gate.contiguous_bank_bytes(slots,256)<=1333739520);
    assert(3*gate.contiguous_bank_bytes(slots+1,256)>1333739520);
    unsigned refused=0;
    try{(void)qwen_app::ExpertQ4Geometry{641,2560}.payload_bytes();}catch(const std::invalid_argument&){++refused;}
    try{(void)gate.contiguous_bank_bytes(9,256);}catch(const std::invalid_argument&){++refused;}
    try{(void)gate.contiguous_bank_bytes(134,18);}catch(const std::invalid_argument&){++refused;}
    try{(void)gate.contiguous_bank_bytes(SIZE_MAX,256);}catch(const std::invalid_argument&){++refused;}
    assert(refused==4);
    std::cout<<"{\"geometry_checks_passed\":true,\"refused_invalid_geometries\":4,\"same_budget_active_slots\":"<<slots<<"}\n";
}
