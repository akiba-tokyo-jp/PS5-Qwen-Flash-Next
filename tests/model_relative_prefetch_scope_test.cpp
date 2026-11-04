// SPDX-License-Identifier: MIT
#include "model_relative_prefetch_scope.h"
#include <iostream>
using namespace qwen_app;
int main(){
    auto zero=model_relative_prefetch_scope(false),one=model_relative_prefetch_scope(true);
    if(require_model_relative_prefetch_scope(zero)||!require_model_relative_prefetch_scope(one))return 1;
    for(unsigned fault=0;fault<12;++fault){
        auto scope=one;
        switch(fault){case 0:scope["prefetch_enabled"]=1;break;case 1:scope["scratch_bytes"]=8u<<20;break;
        case 2:scope["requests"]=1;break;case 3:scope["maximum_extra_workers"]=4;break;
        case 4:scope["maximum_total_parallel_reads"]=5;break;case 5:scope["additional_source_FDs"]=1;break;
        case 6:scope["maximum_predictions_per_original_producer"]=7;break;case 7:scope["model_math_and_GPU_unchanged"]=false;break;
        case 8:scope["persistent_caches"]=true;break;case 9:scope["requests"]=3.0;break;
        case 10:scope.erase("descriptor_identity_fields");break;case 11:scope["unqualified_override"]=true;break;}
        bool refused=false;try{require_model_relative_prefetch_scope(scope);}catch(const std::exception&){refused=true;}if(!refused)return 2;
    }
    std::cout<<nlohmann::json{{"positive_controls",2},{"negative_controls",12},{"control",zero},{"candidate",one}}.dump()<<"\n";
}
