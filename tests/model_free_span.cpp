// SPDX-License-Identifier: MIT
#include "model_free_span.h"
#include <cassert>
int main(){
    const std::int32_t history[]{1,2,1,2,1,2,1,2,1,2};
    auto result=qwen_app::propose_model_free_span(nullptr,0,history,10,100);
    assert(result.found&&result.matches>=2&&(result.tokens==std::array<std::int32_t,3>{1,2,1}));
    result=qwen_app::propose_model_free_span(nullptr,0,history,4,100);assert(!result.found);
    const std::int32_t conflict[]{7,8,1,2,3,7,8,4,5,6};
    const std::int32_t suffix[]{7,8};
    result=qwen_app::propose_model_free_span(conflict,10,suffix,2,100);assert(!result.found);
}
