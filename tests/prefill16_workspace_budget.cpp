// SPDX-License-Identifier: MIT
#include "device_buffer_budget.h"
#include <cassert>
static_assert(qwen_app::model_postload_device_budget==(1792ull<<20));
static_assert(qwen_app::model_postload_single_buffer==(512ull<<20));
static_assert(qwen_app::model_internal_workspace_budget==(248ull<<20));
int main(){
    int key=0;qwen_app::DeviceBufferBudget ledger;ledger.enable();
    ledger.workspace(&key,{32ull<<20,64ull<<20,32ull<<20,0});
    assert(ledger.stats().live==(248ull<<20));ledger.released(&key);ledger.close_completed();
    bool refused=false;qwen_app::DeviceBufferBudget too_wide;too_wide.enable();
    try{too_wide.workspace(&key,{128ull<<20,120ull<<20,1,1});}catch(const std::runtime_error&){refused=true;}
    assert(refused);
    int keys[4]{};qwen_app::DeviceBufferBudget total;total.enable();
    for(auto&k:keys){total.reserve(448ull<<20);total.commit(&k);}
    assert(total.stats().live==(1792ull<<20));refused=false;
    try{total.reserve(2ull<<20);}catch(const std::runtime_error&){refused=true;}
    assert(refused);
}
