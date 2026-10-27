// SPDX-License-Identifier: MIT
#include "resident_counter_baseline.h"
#include <iostream>
int main() {
    const qwen_app::ExpertCacheMetrics total{127,24960,192056524800ull,4096};
    qwen_app::require_resident_context_counter_baseline(total,total);
    unsigned refused=0;
    for(unsigned field=0;field<4;++field)for(bool increment:{false,true}) {
        auto changed=total;
        auto *value=field==0?&changed.hits:field==1?&changed.misses:field==2?&changed.uploaded_bytes:&changed.prefetch_advice_bytes;
        if(increment)++*value;else --*value;
        bool failed=false;try{qwen_app::require_resident_context_counter_baseline(total,changed);}catch(const std::exception &){failed=true;}
        if(!failed)throw std::runtime_error("A changed process-global context baseline was accepted");++refused;
    }
    bool failed=false;try{qwen_app::require_resident_context_counter_baseline(total,{});}catch(const std::exception &){failed=true;}
    if(!failed)throw std::runtime_error("Counter reset must not replace cumulative accounting");
    std::cout<<"{\"nonzero_cumulative_baseline_passed\":true,\"changed_baselines_refused\":"<<refused+1<<"}\n";
}
