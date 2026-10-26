// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <stdexcept>
#include <thread>
namespace qwen_app {
struct RouterShadowRecord {
    std::uint64_t request=0,process=0,early_ns=0,demand_ns=0;
    unsigned layer=0,width=0;
    std::array<std::array<std::int32_t,10>,4> predicted{},actual{};
};
// Fixed storage is charged by sizeof before model creation. Actual cache
// residency and I/O timing must be joined later by request/process/layer IDs;
// matching route IDs alone do not establish useful or timely missing reads.
class RouterShadowObserver {
    const std::thread::id producer_=std::this_thread::get_id();
    const unsigned selected_layer_;
    std::array<RouterShadowRecord,96> records_{};
    unsigned used_=0;
    bool pending_=false,failed_=false,process_active_=false,observed_=false;
    std::uint64_t request_=0,process_=0;
    unsigned width_=0;
    void healthy()const {
        if(std::this_thread::get_id()!=producer_||failed_)throw std::runtime_error("Router shadow producer changed or is quarantined");
    }
    [[noreturn]] void fail(const char *text){failed_=true;throw std::runtime_error(text);}
    static bool valid_ids(const std::int32_t *ids,unsigned width) {
        if(!ids)return false;
        for(unsigned token=0;token<width;++token)for(unsigned i=0;i<10;++i) {
            const auto id=ids[token*10+i];if(id<0||id>=512)return false;
            for(unsigned j=0;j<i;++j)if(id==ids[token*10+j])return false;
        }
        return true;
    }
public:
    explicit RouterShadowObserver(unsigned layer):selected_layer_(layer) {
        if(layer>=48)throw std::invalid_argument("Router shadow must select one original text layer");
    }
    void begin_process(std::uint64_t request,std::uint64_t process,unsigned width) {
        healthy();
        if(process_active_||pending_||!request||!process||width<1||width>4||
           request<request_||(request==request_&&process<=process_)||used_==records_.size())
            throw std::invalid_argument("Fresh bounded router shadow process required before work");
        request_=request;process_=process;width_=width;process_active_=true;observed_=false;
    }
    void early(unsigned layer,const std::int32_t *ids,unsigned width,std::uint64_t now) {
        healthy();
        if(!process_active_||observed_||pending_||layer!=selected_layer_||width!=width_||!now||!valid_ids(ids,width))
            fail("Router shadow early observation differs; graph and source backing must be retained");
        auto &r=records_[used_];r={};r.request=request_;r.process=process_;r.layer=layer;r.width=width;r.early_ns=now;
        for(unsigned t=0;t<width;++t)for(unsigned i=0;i<10;++i)r.predicted[t][i]=ids[t*10+i];
        observed_=true;pending_=true;
    }
    void demand(unsigned layer,const std::int32_t *ids,unsigned width,std::uint64_t now) {
        healthy();
        if(!process_active_||!pending_||layer!=selected_layer_||width!=width_||!now||now<records_[used_].early_ns||!valid_ids(ids,width))
            fail("Router shadow actual-demand observation is stale, missing or invalid");
        auto &r=records_[used_];r.demand_ns=now;
        for(unsigned t=0;t<width;++t)for(unsigned i=0;i<10;++i)r.actual[t][i]=ids[t*10+i];
        pending_=false;++used_;
    }
    void complete_process(bool positive_completion) {
        healthy();
        if(!process_active_||pending_||!observed_||!positive_completion)fail("Router shadow requires returned observations and positive process completion");
        process_active_=false;
    }
    unsigned size()const {healthy();return used_;}
    bool failed()const{return failed_;}
    const RouterShadowRecord &record(unsigned at)const {healthy();if(at>=used_)throw std::out_of_range("Router shadow record is unavailable");return records_[at];}
};
}
