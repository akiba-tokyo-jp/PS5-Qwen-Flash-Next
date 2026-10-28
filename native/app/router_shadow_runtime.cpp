// SPDX-License-Identifier: MIT
#include "router_shadow_runtime.h"
#include "router_shadow_callback.h"
#include "llama-context.h"
#include <memory>
#include <thread>

namespace {
std::unique_ptr<qwen_app::RouterShadowCallback> callback;
llama_context*owner=nullptr;
std::thread::id producer;
std::uint64_t request_id=0,process_id=0;
bool enabled=false,active=false,failed=false,request_active=false;
void healthy(){
    if(!request_active||!owner||failed||std::this_thread::get_id()!=producer)
        throw std::runtime_error("Actual hidden-router observation owner is invalid");
}
}
extern "C" bool qwen_app_router_shadow_graph_enabled(){return enabled;}
namespace qwen_app {
bool evaluate_router_shadow(ggml_tensor*t,bool ask,void*)noexcept{
    if(!enabled||!callback)return false;
    return RouterShadowCallback::evaluate(t,ask,callback.get());
}
void start_router_shadow_request(llama_context*c,std::uint64_t request,bool on,
 ggml_backend_buffer_type_t buffer,void(*guard)(),std::uint64_t(*clock)(),void(*checkpoint)()){
    if(!c||!request||request_active||active||failed||!buffer||!guard||!clock||!checkpoint)
        throw std::invalid_argument("One completed original context is required for hidden-router observation");
    owner=c;request_id=request;process_id=0;producer=std::this_thread::get_id();enabled=on;request_active=true;
    if(on)callback=std::make_unique<RouterShadowCallback>(23,buffer,guard,clock,checkpoint);
    ggml_backend_sched_set_eval_callback(c->get_sched(),evaluate_router_shadow,nullptr);
}
void begin_router_shadow_process(unsigned width){
    healthy();if(active||width<1||width>4)throw std::runtime_error("A fresh bounded hidden-router process is required");
    ++process_id;active=true;if(enabled)callback->observer().begin_process(request_id,process_id,width);
}
void complete_router_shadow_process(){
    healthy();if(!active)throw std::runtime_error("Hidden-router process did not start");
    if(enabled){if(callback->failed()){failed=true;throw std::runtime_error("Native hidden-router callback failed; retain the graph");}
        callback->observer().complete_process(true);}
    active=false;
}
nlohmann::json finish_router_shadow_request(llama_context*c){
    healthy();if(active||c!=owner)throw std::runtime_error("Hidden-router graph must positively complete before release");
    nlohmann::json rows=nlohmann::json::array();
    if(enabled){
        if(callback->failed()||callback->observer().size()!=process_id)throw std::runtime_error("Every original process needs both actual router observations");
        for(unsigned i=0;i<callback->observer().size();++i){const auto&r=callback->observer().record(i);
            rows.push_back({{"request",r.request},{"process",r.process},{"layer",r.layer},{"width",r.width},
                {"early_ns",r.early_ns},{"demand_ns",r.demand_ns},{"predicted",r.predicted},{"actual",r.actual}});}
    }
    nlohmann::json result={{"enabled",enabled},{"layer",23},{"processes",process_id},{"rows",rows},
        {"additional_readback_bytes",enabled?callback->readback_bytes():0},
        {"additional_readback_calls",enabled?callback->readback_calls():0},{"speculative_reads",0},
        {"original_router_owners_reused",true},{"authoritative_expert_selection_unchanged",true}};
    ggml_backend_sched_set_eval_callback(c->get_sched(),evaluate_router_shadow,nullptr);
    callback.reset();owner=nullptr;enabled=false;request_active=false;return result;
}
}
