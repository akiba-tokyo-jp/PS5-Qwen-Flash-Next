// SPDX-License-Identifier: MIT
#include "cold_router_forecast.h"
#include "expert_routing_experiment.h"
#include "profile_clock.h"
#include "llama-context.h"
#include "ggml-backend.h"
#include <array>
#include <cstring>
#include <thread>
namespace {
struct Record {std::array<std::int32_t,6>prediction{},actual{};std::array<bool,6>early_missing{},actual_missing{};std::uint64_t early=0,demand=0,callback_ns=0;};
std::array<Record,96>records;unsigned used=0,request_id=0;bool pending=false,failed=false,active=false;
llama_context*context=nullptr;std::thread::id producer;void(*guard)()=nullptr;void(*checkpoint)()=nullptr;
std::uint64_t stamp(){return std::chrono::duration_cast<std::chrono::nanoseconds>(qwen_app::ProfileClock::now().time_since_epoch()).count();}
void healthy(){if(!active||failed||!context||producer!=std::this_thread::get_id())throw std::runtime_error("Cold router forecast owner differs");}
bool callback(ggml_tensor*t,bool ask,void*)noexcept{
    try{
        if(!active||!qwen_app_route_is_decode()||!t||std::strcmp(t->name,"cold_router_topk-23"))return false;
        healthy();if(ask)return true;
        if(pending||used>=records.size()||t->type!=GGML_TYPE_I32||t->ne[0]!=6||t->ne[1]!=1||t->ne[2]!=1||t->ne[3]!=1||t->nb[0]!=4||!t->buffer)
            throw std::runtime_error("Cold router forecast dimensions or epoch differs");
        auto&r=records[used];r={};const auto start=stamp();guard();ggml_backend_tensor_get(t,r.prediction.data(),0,24);checkpoint();guard();
        for(unsigned i=0;i<6;++i){const auto e=r.prediction[i];if(e<0||e>=512)throw std::runtime_error("Forecast Expert exceeds vocabulary");
            for(unsigned j=0;j<i;++j)if(r.prediction[j]==e)throw std::runtime_error("Forecast repeats an Expert");r.early_missing[i]=!qwen_app_cold_forecast_resident(23,unsigned(e));}
        r.early=stamp();r.callback_ns=r.early-start;pending=true;return true;
    }catch(...){failed=true;return false;}
}
}
namespace qwen_app {
bool evaluate_cold_forecast(ggml_tensor*t,bool ask,void*data)noexcept{return callback(t,ask,data);}
void cold_forecast_begin(llama_context*c,unsigned request,void(*g)(),void(*p)()){
    if(!c||!g||!p||active||pending)throw std::runtime_error("One fresh forecast request required");
    context=c;request_id=request;producer=std::this_thread::get_id();guard=g;checkpoint=p;used=0;pending=false;failed=false;active=true;
    ggml_backend_sched_set_eval_callback(c->get_sched(),callback,nullptr);
}
nlohmann::json cold_forecast_finish(llama_context*c){
    healthy();if(c!=context||pending)throw std::runtime_error("Forecast observations did not complete");
    nlohmann::json rows=nlohmann::json::array();for(unsigned i=0;i<used;++i){const auto&r=records[i];rows.push_back({{"predicted",r.prediction},{"actual",r.actual},{"early_missing",r.early_missing},{"actual_missing",r.actual_missing},{"lead_ns",r.demand-r.early},{"callback_wall_ns",r.callback_ns}});}
    ggml_backend_sched_set_eval_callback(c->get_sched(),nullptr,nullptr);active=false;context=nullptr;
    return {{"request",request_id},{"layer",23},{"decode_width",1},{"selected_Experts",6},{"authoritative_routing_unchanged",true},{"speculative_reads",0},{"additional_GPU_router_projection",true},{"observations",rows}};
}
}
extern "C" void qwen_app_cold_forecast_demand(unsigned layer,const std::int32_t*ids,const std::int32_t*slots){
    if(!active||layer!=23||!qwen_app_route_is_decode())return;healthy();
    if(!pending||!ids||!slots)throw std::runtime_error("Demand has no completed actual early forecast");
    auto&r=records[used];r.demand=stamp();if(r.demand<r.early)throw std::runtime_error("Forecast clock is not monotonic");
    for(unsigned i=0;i<6;++i){if(ids[i]<0||ids[i]>=512)throw std::runtime_error("Actual Expert exceeds vocabulary");r.actual[i]=ids[i];r.actual_missing[i]=slots[ids[i]]<0;}
    pending=false;++used;
}
