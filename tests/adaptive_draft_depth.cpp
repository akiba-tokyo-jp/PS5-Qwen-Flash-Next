// SPDX-License-Identifier: MIT
#include "adaptive_draft_depth.h"
#include <cassert>
int main(){
    using qwen_app::AdaptiveDraftDepth;AdaptiveDraftDepth c;
    assert(c.choose(3,32,true)==1);c.observe(1,1,2,true);
    assert(c.choose(3,32,true)==2);c.observe(2,2,3,true);
    assert(c.choose(3,32,false)==2);assert(c.choose(3,32,true)==4);
    c.observe(4,4,5,true);assert(c.choose(3,32,true)==4);
    assert(c.choose(1,32,true)==2);assert(c.choose(3,2,true)==2);
    assert(c.choose(0,32,true)==1);assert(c.choose(3,1,true)==1);
    for(int i=0;i<12;++i)c.observe(4,1,12,true);
    assert(c.choose(3,32,true)==2);
    for(int i=0;i<12;++i)c.observe(2,1,12,true);
    assert(c.choose(3,32,true)==1);
    bool refused=false;try{c.observe(4,4,1,false);}catch(const std::invalid_argument&){refused=true;}assert(refused);
    AdaptiveDraftDepth reset;assert(reset.choose(3,32,true)==1);
}
