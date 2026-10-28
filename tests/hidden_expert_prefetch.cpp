// SPDX-License-Identifier: MIT
#include "hidden_expert_prefetch.h"
#include <cassert>
int main(){
    qwen_app::HiddenExpertPrefetch h;int owner=0,other=0,calls=0;
    h.bind(&owner,[&](unsigned layer,int id){assert(layer==23&&id==411);++calls;});
    h.propose(23,411,1);assert(calls==0);h.select(true);
    h.propose(23,411,4);assert(calls==0);h.propose(23,411,1);assert(calls==1);
    bool refused=false;try{h.bind(&other,[](unsigned,int){});}catch(const std::invalid_argument&){refused=true;}assert(refused);
    refused=false;try{h.propose(23,512,1);}catch(const std::invalid_argument&){refused=true;}assert(refused);
    refused=false;std::thread t([&]{try{h.propose(23,411,1);}catch(const std::runtime_error&){refused=true;}});t.join();assert(refused);
    refused=false;try{h.unbind(&other);}catch(const std::runtime_error&){refused=true;}assert(refused);
    h.unbind(&owner);assert(!h.enabled()&&!h.owns(&owner));
}
