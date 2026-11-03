// SPDX-License-Identifier: MIT
#include "model_relative_prefetch.h"
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <vector>
using namespace qwen_app;
static thread_local bool demand=false;
static void check(bool b){if(!b)throw std::runtime_error("Concurrent relative-prefetch control failed");}
enum Mode{GOOD,SHORT,IDENTITY,DECLINE,CLOSE_DRAIN,CONCURRENT,THROW_WORKER,WORKER_ADMISSION};
struct Fixture {
    Mode mode;std::thread::id main=std::this_thread::get_id();std::mutex mutex;std::condition_variable changed;
    bool hold_worker=false,hold_demands=false,worker_entered=false,worker_finished=false;
    unsigned demand_entered=0,active=0,peak=0,closed=0,worker_reads=0;
    std::shared_ptr<void>backing;void*scratch=nullptr;std::unique_ptr<ModelRelativePrefetch>owner;
    explicit Fixture(Mode value):mode(value){
        void*raw=std::malloc((2u<<20)+16384);check(raw);backing=std::shared_ptr<void>(raw,std::free);
        scratch=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(raw)+16383)&~std::uintptr_t(16383));
        RelativePrefetchHooks hooks;
        hooks.inspect=[this](int fd){ObservedReadIdentity i;i.valid=true;i.flags=65536;
            i.fields={1,std::uint64_t(fd),256u<<20,0100444,0,0,0,0,1,0,1,0};
            std::lock_guard<std::mutex>lock(mutex);if(!demand&&mode==IDENTITY&&worker_reads)++i.fields[1];return i;};
        hooks.read=[this](int,void*to,std::size_t bytes,std::int64_t offset)->std::int64_t{
            const bool foreground=demand;{
                std::unique_lock<std::mutex>lock(mutex);++active;peak=std::max(peak,active);
                if(!foreground){worker_entered=true;++worker_reads;changed.notify_all();changed.wait(lock,[&]{return !hold_worker;});}
                else if(std::this_thread::get_id()!=main){++demand_entered;changed.notify_all();changed.wait(lock,[&]{return !hold_demands;});}
            }
            if(!foreground&&mode==THROW_WORKER){std::lock_guard<std::mutex>lock(mutex);--active;worker_finished=true;changed.notify_all();throw std::runtime_error("Opaque returned worker exception");}
            for(std::size_t i=0;i<bytes;++i)static_cast<unsigned char*>(to)[i]=static_cast<unsigned char>((std::uint64_t(offset)/16384)^i);
            {std::lock_guard<std::mutex>lock(mutex);--active;if(!foreground)worker_finished=true;changed.notify_all();}
            if(!foreground&&mode==SHORT)return std::int64_t(bytes)-1;
            errno=37;return std::int64_t(bytes);
        };
        hooks.close=[this](int){std::lock_guard<std::mutex>lock(mutex);check(!active);++closed;errno=29;return 0;};
        hooks.admit=[this](std::size_t){return mode!=DECLINE&&(mode!=WORKER_ADMISSION||demand);};
        owner=std::make_unique<ModelRelativePrefetch>(std::move(hooks),scratch,2u<<20,backing);owner->begin_request();
    }
    void wait(const std::function<bool()>&predicate){
        std::unique_lock<std::mutex>lock(mutex);check(changed.wait_for(lock,std::chrono::seconds(2),predicate));
    }
    void ready(){
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(2);
        while(!owner->pending_returned()){check(std::chrono::steady_clock::now()<deadline);std::this_thread::yield();}
    }
    void read(unsigned index,int fd=3){
        demand=true;std::vector<unsigned char>to(256u<<10);errno=11;
        check(owner->read(fd,to.data(),to.size(),std::int64_t(index)*(256u<<10))==std::int64_t(to.size()));
        for(std::size_t i=0;i<to.size();++i)check(to[i]==static_cast<unsigned char>((index*16)^i));
        check(errno==11||errno==37);
    }
    void train(){for(unsigned i=0;i<4;++i)read(i);}
};
int main(){
    unsigned passed=0;
    for(Mode mode:{GOOD,SHORT,IDENTITY,DECLINE,WORKER_ADMISSION}){
        Fixture f(mode);f.train();if(mode!=DECLINE)f.ready();f.read(4);
        const auto stats=f.owner->finish_request();check(stats.maximum_simultaneous_reads<=4&&stats.worker_creations<=1);
        if(mode==GOOD)check(stats.hits==1&&stats.original_reads==4&&stats.positive_worker_reads>=1);
        else check(!stats.hits&&stats.original_reads==5);
        if(mode==WORKER_ADMISSION)check(stats.worker_creations==1&&stats.predictions>=1&&!stats.speculative_reads);
        if(mode==DECLINE)check(!stats.worker_creations&&!stats.predictions&&!stats.speculative_reads);
        else check(stats.speculative_reads==stats.speculative_returned_calls&&stats.completed_worker_jobs==stats.predictions);
        check(stats.hits+stats.unused==stats.predictions);check(!f.owner->close_source(3)&&f.closed==1);
        f.owner->close_completed();++passed;
    }
    {
        Fixture f(CLOSE_DRAIN);f.hold_worker=true;f.train();f.wait([&]{return f.worker_entered;});
        std::thread release([&]{std::this_thread::sleep_for(std::chrono::milliseconds(20));
            std::lock_guard<std::mutex>lock(f.mutex);check(!f.closed);f.hold_worker=false;f.changed.notify_all();});
        check(!f.owner->close_source(3));release.join();check(f.closed==1&&f.worker_finished);
        const auto stats=f.owner->finish_request();check(stats.unused==1&&stats.speculative_returned_calls==1);
        f.owner->close_completed();++passed;
    }
    {
        Fixture f(CONCURRENT);f.hold_worker=true;f.train();f.wait([&]{return f.worker_entered;});
        f.hold_demands=true;std::vector<std::thread>workers;
        for(int i=0;i<4;++i)workers.emplace_back([&,i]{f.read(0,10+i);});
        f.wait([&]{return f.demand_entered==3;});
        {std::lock_guard<std::mutex>lock(f.mutex);check(f.active==4&&f.peak==4);f.hold_worker=false;f.changed.notify_all();}
        f.wait([&]{return f.demand_entered==4;});
        {std::lock_guard<std::mutex>lock(f.mutex);check(f.active==4&&f.peak==4);f.hold_demands=false;f.changed.notify_all();}
        for(auto&t:workers)t.join();const auto stats=f.owner->finish_request();
        check(stats.maximum_simultaneous_reads==4&&stats.original_reads==8&&stats.worker_creations==1&&stats.unused==1);
        check(!f.owner->close_source(3));for(int i=0;i<4;++i)check(!f.owner->close_source(10+i));
        f.owner->close_completed();++passed;
    }
    {
        Fixture f(GOOD);bool refused=false;try{f.owner->begin_request();}catch(const std::runtime_error&){refused=true;}check(refused);
        f.owner->finish_request();f.owner->close_completed();++passed;
    }
    {
        Fixture f(THROW_WORKER);f.train();f.wait([&]{return f.worker_finished;});
        bool refused=false;try{f.owner->finish_request();}catch(const std::runtime_error&){refused=true;}check(refused);
        refused=false;try{f.owner->close_source(3);}catch(const std::runtime_error&){refused=true;}check(refused&&!f.closed);
        auto held=std::weak_ptr<void>(f.backing);f.owner.reset();f.backing.reset();check(!held.expired());++passed;
    }
    std::cout<<"model_relative_prefetch_controls="<<passed<<" original_maximum_parallel_reads=4 extra_fds=0 PS5_operations=0\n";
}
