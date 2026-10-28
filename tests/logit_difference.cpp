// SPDX-License-Identifier: MIT
#include "logit_difference.h"
#include <cassert>
#include <limits>
int main(){
    const float reference[]={1,2,3,4,5,6,7,8};float candidate[8],scratch[8];
    for(unsigned i=0;i<8;++i)candidate[i]=reference[i];
    auto exact=qwen_app::compare_logits(candidate,reference,8,scratch);
    assert(exact.finite&&exact.maximum==0&&exact.outside_tolerance==0&&exact.KL_reference_to_candidate==0);
    for(unsigned i=0;i<8;++i)candidate[i]=reference[i]+2;
    auto shifted=qwen_app::compare_logits(candidate,reference,8,scratch);
    assert(shifted.maximum==2&&shifted.rms==2&&shifted.centered_rms==0&&shifted.outside_tolerance==8);
    assert(shifted.KL_reference_to_candidate<1e-12&&shifted.reference_top==shifted.candidate_top);
    candidate[0]=20;
    auto changed=qwen_app::compare_logits(candidate,reference,8,scratch);
    assert(changed.candidate_top[0]==0&&changed.reference_top[0]==7&&changed.KL_reference_to_candidate>1);
    candidate[2]=std::numeric_limits<float>::quiet_NaN();
    assert(!qwen_app::compare_logits(candidate,reference,8,scratch).finite);
    assert(!qwen_app::compare_logits(nullptr,reference,8,scratch).finite);
    assert(!qwen_app::compare_logits(candidate,reference,4,scratch).finite);
}
