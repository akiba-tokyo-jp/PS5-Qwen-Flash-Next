// SPDX-License-Identifier: MIT
#pragma once
#include <functional>
#include <stdexcept>
#include <thread>
namespace qwen_app {
// The callback executes only on the original producer after the early GPU
// readback fence. The existing worker owns every submitted source/bank lease.
class HiddenExpertPrefetch {
    const void*owner_=nullptr;
    std::thread::id producer_{};
    std::function<void(unsigned,int)> submit_;
    bool enabled_=false;
    void producer()const{
        if(!owner_||std::this_thread::get_id()!=producer_)
            throw std::runtime_error("Hidden Expert prediction requires its original cache producer");
    }
public:
    void bind(const void*owner,std::function<void(unsigned,int)>submit){
        if(!owner||owner_||!submit)throw std::invalid_argument("One actual original Expert cache is required");
        owner_=owner;producer_=std::this_thread::get_id();submit_=std::move(submit);
    }
    void unbind(const void*owner){
        producer();if(owner!=owner_)throw std::runtime_error("Hidden Expert cache owner differs");
        enabled_=false;submit_={};owner_=nullptr;
    }
    void select(bool enabled){producer();enabled_=enabled;}
    bool enabled()const{return enabled_;}
    bool owns(const void*owner)const{return owner_==owner&&owner;}
    void propose(unsigned layer,int expert,unsigned width){
        producer();if(!enabled_||width!=1)return;
        if(layer!=23||expert<0||expert>=512)throw std::invalid_argument("One actual layer-23 Expert is required");
        submit_(layer,expert);
    }
};
inline HiddenExpertPrefetch hidden_expert_prefetch;
}
