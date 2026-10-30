// SPDX-License-Identifier: MIT
#include "expert_routing_policy.h"
#include <cassert>
int main(){
    for(unsigned code:{0u,1u,2u,4u,5u,6u,8u,9u,10u,12u,13u,14u}){
        const auto p=qwen_app::routing_policy(code);
        assert(qwen_app::decode_policy_experts(code,1)==p.experts);
        assert(qwen_app::decode_policy_experts(code,2)==p.experts);
        assert(qwen_app::decode_policy_experts(code,4)==10);
        assert(p.cache_rank==bool(code&4)&&p.sharing==bool(code&8));
    }
    for(unsigned code:{3u,7u,11u,15u,16u}){
        bool refused=false;try{(void)qwen_app::routing_policy(code);}catch(const std::exception&){refused=true;}assert(refused);
    }
    assert(qwen_app::routing_policy(6).experts==6&&qwen_app::routing_policy(14).sharing);
}
