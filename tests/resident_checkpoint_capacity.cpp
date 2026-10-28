// SPDX-License-Identifier: MIT
#include "resident_checkpoint_capacity.h"
#include <cassert>
template<class F>void refuses(F fn){bool failed=false;try{fn();}catch(const std::runtime_error&){failed=true;}assert(failed);}
int main(){
    qwen_app::ResidentCheckpointCapacity c;int first=0,second=0;
    constexpr std::uint64_t payload=118038528,rounded=119537664;
    assert(c.new_allocation(&first,payload)==rounded);
    refuses([&]{c.completed(&first,payload,false);});
    assert(c.new_allocation(&first,payload)==rounded);
    c.completed(&first,payload,true);
    assert(c.new_allocation(&first,payload)==0);
    assert(c.new_allocation(&first,payload+1)==rounded);
    refuses([&]{c.new_allocation(&second,payload);});
    refuses([&]{c.completed(&second,payload,true);});
    refuses([&]{c.new_allocation(nullptr,payload);});
    refuses([&]{c.new_allocation(&first,0);});
    refuses([&]{c.new_allocation(&first,(136ull<<20)+1);});
    c.completed(&first,payload+1,true);
    assert(c.new_allocation(&first,payload+1)==0);
    assert(c.new_allocation(&first,payload)==rounded);
}
