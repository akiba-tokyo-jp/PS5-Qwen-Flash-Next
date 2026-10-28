// SPDX-License-Identifier: MIT
#include "predictive_model_geometry.h"
#include <array>
#include <iostream>
#include <stdexcept>
int main(){
    using qwen_app::original_predictive_model_geometry;
    if(!original_predictive_model_geometry(48,49,1,512,10))throw std::runtime_error("Original retained MTP geometry refused");
    std::array<unsigned,5> values{48,49,1,512,10};unsigned controls=0;
    for(unsigned field=0;field<5;++field)for(int delta:{-1,1}){auto changed=values;changed[field]+=delta;
        if(original_predictive_model_geometry(changed[0],changed[1],changed[2],changed[3],changed[4]))throw std::runtime_error("Altered model geometry accepted");++controls;}
    std::cout<<"{\"original_trunk_layers\":48,\"retained_MTP_layers\":1,\"negative_controls\":"<<controls<<"}\n";
}
