// SPDX-License-Identifier: MIT
#include "completed_read_pool.h"
#include <cassert>
#include <iostream>
using namespace qwen_app;
static unsigned char storage[5*16384];
int main(){
    const auto aligned=(reinterpret_cast<std::uintptr_t>(storage)+16383)&~std::uintptr_t(16383);
    std::array<BoundedReadRequest,4>requests{};for(unsigned i=0;i<4;++i)requests[i]={int(i),reinterpret_cast<void*>(aligned+i*16384),16384,0};
    const auto producer=std::this_thread::get_id();std::mutex mutex;std::condition_variable changed;bool release=false;
    CompletedReadPool pool([&](const BoundedReadRequest&r){
        if(r.fd==0){std::unique_lock<std::mutex>lock(mutex);changed.wait(lock,[&]{return release;});}
        return std::int64_t(r.bytes);
    });pool.start();unsigned consumed=0;bool early=false;
    pool.read_each(requests,[&](unsigned i,std::int64_t got){
        assert(std::this_thread::get_id()==producer&&got==16384);++consumed;
        if(i!=0){std::lock_guard<std::mutex>lock(mutex);if(!release){early=true;release=true;changed.notify_all();}}
    });assert(early&&consumed==4);pool.require_completed();pool.stop_completed();
    for(bool callback_failure:{false,true}){
        std::atomic<unsigned>finished{0};unsigned callbacks=0;
        CompletedReadPool failed([&](const BoundedReadRequest&r){++finished;return std::int64_t(r.bytes-(callback_failure?0:1));});failed.start();
        bool threw=false;try{failed.read_each(requests,[&](unsigned,std::int64_t){++callbacks;throw std::runtime_error("Injected callback failure");});}catch(const std::runtime_error&){threw=true;}
        assert(threw&&finished==4&&callbacks==(callback_failure?1u:0u));failed.require_completed();failed.stop_completed();
    }
    CompletedReadPool invalid([](const BoundedReadRequest&r){return std::int64_t(r.bytes);});invalid.start();
    requests[1].target=requests[0].target;bool overlap=false;try{invalid.read_each(requests,[](unsigned,std::int64_t){});}catch(const std::invalid_argument&){overlap=true;}
    assert(overlap);invalid.require_completed();invalid.stop_completed();
    std::cout<<"Completion callbacks precede slow reads, stay on producer, and drain all failure paths.\n";
}
