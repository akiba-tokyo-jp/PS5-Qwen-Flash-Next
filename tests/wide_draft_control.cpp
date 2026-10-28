// SPDX-License-Identifier: MIT
#include "wide_draft_control.h"
#include <cassert>
#include <limits>
namespace qwen_app {WideDraftControl wide_draft_control;}
int main(){
    using namespace qwen_app;
    int a=0,b=0;WideDraftControl c;
    auto p=c.consume(&a,3);assert(p.width==2&&p.drafts[0]==3);
    c.arm(&a,{7,8,9});
    bool refused=false;try{c.consume(&b,7);}catch(const std::invalid_argument&){refused=true;}assert(refused);
    p=c.consume(&a,7);assert(p.width==4&&p.drafts[2]==9);c.decision(2);assert(c.last_prefix()==2);
    std::vector<float> q{1,2,3,4,5,6},v;bool more=false;
    pop_verified_logits(q,v,2,more);assert((v==std::vector<float>{1,2})&&more);
    pop_verified_logits(q,v,2,more);assert((v==std::vector<float>{3,4})&&more);
    pop_verified_logits(q,v,2,more);assert((v==std::vector<float>{5,6})&&!more&&q.empty());
    refused=false;try{pop_verified_logits(q,v,2,more);}catch(const std::invalid_argument&){refused=true;}assert(refused);
    q={1,std::numeric_limits<float>::quiet_NaN()};refused=false;
    try{pop_verified_logits(q,v,2,more);}catch(const std::invalid_argument&){refused=true;}assert(refused);
}
