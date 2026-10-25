// SPDX-License-Identifier: MIT
#include "demand_source_batch.h"
#include <atomic>
#include <cstdlib>
#include <malloc.h>
#include <cstring>
#include <cstdio>
#include <stdexcept>
namespace {
unsigned controls=0;
void require(bool x){++controls;if(!x)throw std::runtime_error("Demand batch control failed");}
struct State {
    std::mutex mutex;std::condition_variable changed;
    std::atomic<unsigned> active{0},peak{0},calls{0};bool third=false,force=false,short_read=false;
};
std::int64_t read(void *opaque,const qwen_app::CompletionRead &r) {
    auto &s=*static_cast<State *>(opaque);++s.calls;
    unsigned active=++s.active,old=s.peak.load();while(old<active&&!s.peak.compare_exchange_weak(old,active)){}
    if(s.force&&r.id==0) {
        std::unique_lock<std::mutex> lock(s.mutex);
        if(!s.changed.wait_for(lock,std::chrono::seconds(2),[&]{return s.third;}))throw std::runtime_error("Refill did not progress");
    }
    if(r.id==2){std::lock_guard<std::mutex> lock(s.mutex);s.third=true;s.changed.notify_all();}
    std::memset(r.target,int(r.id+1),r.bytes);--s.active;
    return static_cast<std::int64_t>(r.bytes)-(s.short_read&&r.id==1?1:0);
}
}
int main()try {
    void *memory=_aligned_malloc(40*16384,16384);require(memory!=nullptr);
    std::array<qwen_app::CompletionRead,40> requests;
    for(unsigned i=0;i<40;++i)requests[i]={1,static_cast<unsigned char *>(memory)+i*16384,16384,i*16384,i};
    State s;s.force=true;qwen_app::DemandSourceBatch batch(read,&s);batch.start();batch.read(requests.data(),6);
    require(s.third&&s.peak==2&&s.calls==6&&s.active==0);batch.require_completed();
    for(unsigned i=0;i<6;++i)require(static_cast<unsigned char *>(requests[i].target)[16383]==i+1);
    auto bad=requests;bad[1].target=bad[0].target;bool refused=false;
    try{batch.read(bad.data(),6);}catch(const std::invalid_argument&){refused=true;}
    require(refused&&s.calls==6);s.force=false;batch.read(requests.data(),40);require(s.calls==46);
    for(unsigned i=0;i<40;++i)require(static_cast<unsigned char *>(requests[i].target)[16383]==i+1);
    batch.stop_completed();
    State failure;failure.short_read=true;qwen_app::DemandSourceBatch failed(read,&failure);failed.start();refused=false;
    try{failed.read(requests.data(),6);}catch(const std::runtime_error&){refused=true;}
    require(refused&&failure.active==0&&failed.completion_known());failed.stop_completed();_aligned_free(memory);
    std::printf("{\"controls\":%u,\"refill_while_other_read_pending\":true,\"maximum_live_reads\":2,\"known_failure_joined\":true}\n",controls);
    return 0;
}catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}
