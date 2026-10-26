// SPDX-License-Identifier: MIT
#pragma once
#include "router_shadow_observer.h"
#include "ggml-backend.h"
#include <cstdio>
#include <cstring>
namespace qwen_app {
class RouterShadowCallback {
    RouterShadowObserver observer_;
    const unsigned layer_;
    ggml_backend_buffer_type_t expected_buffer_;
    void (*guard_)();
    std::uint64_t (*clock_)();
    void (*checkpoint_)();
    std::array<char,64> early_name_{},actual_name_{};
    bool failed_=false;
    std::uint64_t readback_bytes_=0,readback_calls_=0;
public:
    RouterShadowCallback(unsigned layer,ggml_backend_buffer_type_t buffer,void(*guard)(),std::uint64_t(*clock)(),void(*checkpoint)()):
        observer_(layer),layer_(layer),expected_buffer_(buffer),guard_(guard),clock_(clock),checkpoint_(checkpoint) {
        if(!buffer||!guard||!clock||!checkpoint)throw std::invalid_argument("Router shadow requires qualified backing, memory, clock and completion hooks");
        std::snprintf(early_name_.data(),early_name_.size(),"qwen_router_shadow_topk-%u",layer);
        std::snprintf(actual_name_.data(),actual_name_.size(),"ffn_moe_topk-%u",layer);
    }
    RouterShadowObserver &observer(){return observer_;}
    bool failed()const{return failed_||observer_.failed();}
    std::uint64_t readback_bytes()const{return readback_bytes_;}
    std::uint64_t readback_calls()const{return readback_calls_;}
    static bool evaluate(ggml_tensor *tensor,bool ask,void *opaque) noexcept {
        if(!opaque)return false;
        auto &self=*static_cast<RouterShadowCallback *>(opaque);
        try {
            if(self.failed()||!tensor)return false;
            const bool early=!std::strcmp(tensor->name,self.early_name_.data());
            const bool actual=!std::strcmp(tensor->name,self.actual_name_.data());
            if(ask)return early||actual;
            if(!early&&!actual)throw std::runtime_error("Unexpected router shadow completion callback");
            if(tensor->type!=GGML_TYPE_I32||tensor->ne[0]!=10||tensor->ne[1]<1||tensor->ne[1]>4||
               tensor->ne[2]!=1||tensor->ne[3]!=1||tensor->nb[0]!=4||tensor->nb[1]<40||!tensor->buffer||
               ggml_backend_buffer_get_type(tensor->buffer)!=self.expected_buffer_)
                throw std::runtime_error("Router shadow readback shape or actual GPU buffer differs");
            self.guard_();std::array<std::int32_t,40> ids{};
            // Top-k is a view of the full argsort. Read only ten IDs in each
            // actual row; do not assume contiguous rows or copy the full tensor.
            for(unsigned token=0;token<unsigned(tensor->ne[1]);++token) {
                ggml_backend_tensor_get(tensor,ids.data()+10*token,token*tensor->nb[1],40);
                ++self.readback_calls_;self.readback_bytes_+=40;
            }
            self.checkpoint_();self.guard_();const auto now=self.clock_();
            if(early)self.observer_.early(self.layer_,ids.data(),unsigned(tensor->ne[1]),now);
            else self.observer_.demand(self.layer_,ids.data(),unsigned(tensor->ne[1]),now);
            return true;
        }catch(...){self.failed_=true;return false;}
    }
};
}
