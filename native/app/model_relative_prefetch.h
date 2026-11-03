// SPDX-License-Identifier: MIT
#pragma once
#include "relative_span_predictor.h"
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <functional>
#include <memory>
#include <mutex>
#include <thread>

namespace qwen_app {
struct RelativePrefetchHooks {
    std::function<std::int64_t(int,void*,std::size_t,std::int64_t)>read;
    std::function<ObservedReadIdentity(int)>inspect;
    std::function<int(int)>close;
    std::function<bool(std::size_t)>admit;
};
struct RelativePrefetchStats {
    std::uint64_t original_reads=0,original_bytes=0,predictions=0,predicted_bytes=0;
    std::uint64_t hits=0,hit_bytes=0,unused=0,invalid=0,declines=0;
    std::uint64_t maximum_simultaneous_reads=0,worker_creations=0,positive_worker_reads=0;
    std::uint64_t speculative_reads=0,speculative_returned_calls=0,speculative_bytes=0,completed_worker_jobs=0;
};

// One optional worker and one actual scratch lease. The original producers
// remain concurrent, sharing their four-read limit with speculative I/O.
// A wrapped original close drains the same fd before forwarding that close.
// Unknown completion keeps the entire state, fd and backing until OS close.
class ModelRelativePrefetch {
    struct Producer {RelativeSpanPredictor predictor;unsigned submitted=0;};
    struct State {
        RelativePrefetchHooks hooks;void*scratch;std::size_t capacity;std::shared_ptr<void>backing;
        std::mutex mutex;std::condition_variable changed;std::thread worker;
        std::map<std::thread::id,std::unique_ptr<Producer>>producers;
        std::map<int,unsigned>active_fd;
        std::map<int,ObservedReadIdentity>known_fd;
        RelativePrefetchStats stats;
        RelativeSpan pending_span{};std::thread::id pending_producer;
        int pending_fd=-1;std::uint64_t active=0,inflight=0;
        bool enabled=false,pending=false,job=false,done=true,valid=false,stop=false,unknown=false;
        State(RelativePrefetchHooks h,void*p,std::size_t n,std::shared_ptr<void>b):
            hooks(std::move(h)),scratch(p),capacity(n),backing(std::move(b)){}
    };
    State*s_=nullptr;const std::thread::id owner_=std::this_thread::get_id();
    static void require(bool condition,const char*message){if(!condition)throw std::runtime_error(message);}
    static bool same(const ObservedReadIdentity&a,const RelativeSpan&b){return a.valid&&a.fields==b.identity&&a.flags==b.flags;}
    static void peak(State&s){s.stats.maximum_simultaneous_reads=std::max(s.stats.maximum_simultaneous_reads,s.inflight);}
    static void wait_done(State&s,std::unique_lock<std::mutex>&lock){
        if(!s.changed.wait_for(lock,std::chrono::seconds(10),[&]{return s.done;})){
            s.unknown=true;throw std::runtime_error("Relative prefetch completion unknown; retain original fd and all backing");}
        require(!s.unknown,"Relative prefetch owner is quarantined; retain backing");
    }
    static void discard(State&s){if(s.pending){require(s.done,"Only positively returned prefetch may be discarded");++s.stats.unused;s.pending=false;s.valid=false;s.pending_fd=-1;}}
    static void start_worker(State&s){
        if(s.worker.joinable())return;
        s.worker=std::thread([&s]{
            std::unique_lock<std::mutex>lock(s.mutex);
            for(;;){
                s.changed.wait(lock,[&]{return s.job||s.stop;});if(s.stop)return;
                const auto key=s.pending_span;const int fd=s.pending_fd;s.job=false;lock.unlock();bool valid=false,read=false;
                std::int64_t got=-1;
                try{
                    const auto first=s.hooks.inspect(fd);
                    if(s.hooks.admit(std::size_t(key.bytes))&&same(first,key)){
                        read=true;got=s.hooks.read(fd,s.scratch,std::size_t(key.bytes),std::int64_t(key.offset));
                        const auto last=s.hooks.inspect(fd);valid=got==std::int64_t(key.bytes)&&same(last,key);
                    }
                }catch(...){lock.lock();s.unknown=true;s.changed.notify_all();return;}
                lock.lock();s.valid=valid;s.done=true;--s.inflight;
                ++s.stats.completed_worker_jobs;
                if(read){++s.stats.speculative_reads;++s.stats.speculative_returned_calls;if(got>0)s.stats.speculative_bytes+=std::uint64_t(got);}
                if(valid)++s.stats.positive_worker_reads;else ++s.stats.invalid;s.changed.notify_all();
            }
        });++s.stats.worker_creations;
    }
public:
    ModelRelativePrefetch(RelativePrefetchHooks hooks,void*scratch,std::size_t capacity,std::shared_ptr<void>backing){
        require(hooks.read&&hooks.inspect&&hooks.close&&hooks.admit&&scratch&&backing&&
            capacity==(2u<<20)&&!(reinterpret_cast<std::uintptr_t>(scratch)%16384),
            "Exact hooks and an actual aligned two-MiB scratch lease required");
        s_=new State(std::move(hooks),scratch,capacity,std::move(backing));
    }
    ModelRelativePrefetch(const ModelRelativePrefetch&)=delete;
    ModelRelativePrefetch&operator=(const ModelRelativePrefetch&)=delete;
    // Explicit positive stop is mandatory; a destructor never cancels I/O.
    ~ModelRelativePrefetch()=default;
    bool pending_returned()const{
        require(s_,"A live prefetch state is required");std::lock_guard<std::mutex>lock(s_->mutex);
        return s_->pending&&s_->done&&!s_->unknown;
    }
    void begin_request(){
        require(owner_==std::this_thread::get_id()&&s_,"Original live prefetch owner required");
        auto&s=*s_;std::lock_guard<std::mutex>lock(s.mutex);
        require(!s.enabled&&!s.pending&&!s.active&&!s.unknown&&!s.stop,"Completed previous source request required");
        s.producers.clear();s.enabled=true;
    }
    std::int64_t read(int fd,void*destination,std::size_t bytes,std::int64_t offset){
        auto&s=*s_;const int incoming=errno;std::unique_lock<std::mutex>lock(s.mutex);
        require(!s.unknown,"Relative prefetch is quarantined; retain original source ownership");
        if(!s.enabled){lock.unlock();errno=incoming;return s.hooks.read(fd,destination,bytes,offset);}
        ++s.active;++s.active_fd[fd];const auto thread=std::this_thread::get_id();lock.unlock();
        ObservedReadRow row;row.descriptor=fd;row.offset=std::uint64_t(offset);row.requested=bytes;
        row.candidate=destination&&offset>=0&&bytes>=(256u<<10)&&bytes<=(8u<<20)&&!((bytes|std::size_t(offset))%16384);
        ObservedReadIdentity before{};
        if(row.candidate){before=s.hooks.inspect(fd);row.before=before.fields;row.flags_before=before.flags;row.before_valid=before.valid;}
        lock.lock();
        if(before.valid)s.known_fd[fd]=before;
        bool hit=false;
        if(s.pending&&s.pending_producer==thread&&s.done){
            const auto&key=s.pending_span;
            if(row.candidate&&fd==s.pending_fd&&same(before,key)&&bytes==key.bytes&&std::uint64_t(offset)==key.offset&&s.valid){
                const auto after=s.hooks.inspect(fd);
                if(same(after,key)){std::memcpy(destination,s.scratch,bytes);hit=true;++s.stats.hits;s.stats.hit_bytes+=bytes;}
            }
            if(!hit)discard(s);else {s.pending=false;s.valid=false;s.pending_fd=-1;}
        }
        std::int64_t result=std::int64_t(bytes);int returned_errno=incoming;
        if(!hit){
            if(!s.changed.wait_for(lock,std::chrono::seconds(10),[&]{return s.inflight<4||s.unknown;})){
                s.unknown=true;throw std::runtime_error("Original source slot completion unknown; retain all owners");}
            require(!s.unknown,"A quarantined source slot cannot be reused");
            ++s.inflight;peak(s);lock.unlock();errno=incoming;
            result=s.hooks.read(fd,destination,bytes,offset);returned_errno=errno;
            lock.lock();--s.inflight;++s.stats.original_reads;
            if(result>0)s.stats.original_bytes+=std::uint64_t(result);s.changed.notify_all();
        }
        lock.unlock();
        row.returned=result;
        if(row.candidate){const auto after=s.hooks.inspect(fd);row.after=after.fields;row.flags_after=after.flags;row.after_valid=after.valid;}
        row.identity_equal=row.before_valid&&row.after_valid&&row.before==row.after&&row.flags_before==row.flags_after;
        lock.lock();
        auto found=s.producers.find(thread);
        if(found==s.producers.end()&&row.candidate&&s.producers.size()<8)found=s.producers.emplace(thread,std::make_unique<Producer>()).first;
        std::optional<RelativeSpan>target;
        if(found!=s.producers.end())target=found->second->predictor.complete(row);
        if(target&&target->bytes<=s.capacity&&found->second->submitted<6&&!s.pending&&s.inflight<3){
            lock.unlock();const bool admitted=s.hooks.admit(std::size_t(target->bytes));lock.lock();
            if(admitted&&!s.pending&&s.inflight<3&&!s.unknown&&s.enabled){
                const auto current=s.hooks.inspect(fd);
                if(same(current,*target)){
                    start_worker(s);s.pending_span=*target;s.pending_fd=fd;s.pending_producer=thread;
                    s.pending=true;s.valid=false;s.done=false;s.job=true;++s.inflight;peak(s);
                    ++found->second->submitted;++s.stats.predictions;s.stats.predicted_bytes+=target->bytes;s.changed.notify_all();
                }else ++s.stats.declines;
            }else ++s.stats.declines;
        }
        --s.active;--s.active_fd[fd];s.changed.notify_all();lock.unlock();errno=returned_errno;return result;
    }
    int close_source(int fd){
        auto&s=*s_;const int incoming=errno;std::unique_lock<std::mutex>lock(s.mutex);
        if(!s.known_fd.count(fd)){lock.unlock();errno=incoming;return s.hooks.close(fd);}
        require(!s.unknown&&!s.active_fd[fd],"Original source close requires all original reads returned");
        if(s.pending&&s.pending_fd==fd){wait_done(s,lock);discard(s);}
        // The original source owner has already joined its demand producers.
        // Keep this lock through the one original close to exclude a new lease.
        errno=incoming;const int result=s.hooks.close(fd);const int error=errno;
        if(!result){s.known_fd.erase(fd);s.active_fd.erase(fd);}else s.unknown=true;
        lock.unlock();errno=error;return result;
    }
    RelativePrefetchStats finish_request(){
        require(owner_==std::this_thread::get_id()&&s_,"Original prefetch completion owner required");
        auto&s=*s_;std::unique_lock<std::mutex>lock(s.mutex);
        require(s.enabled&&!s.active&&!s.unknown,"Original demand completion must precede prefetch retirement");
        s.enabled=false;if(s.pending){wait_done(s,lock);discard(s);}return s.stats;
    }
    RelativePrefetchStats close_completed(){
        require(owner_==std::this_thread::get_id()&&s_,"Original prefetch retirement owner required");
        auto*s=s_;std::unique_lock<std::mutex>lock(s->mutex);
        require(!s->enabled&&!s->active&&!s->pending&&s->done&&!s->inflight&&!s->unknown,
            "Every original and speculative read must positively return before retirement");
        s->stop=true;s->changed.notify_all();const auto stats=s->stats;lock.unlock();
        if(s->worker.joinable())s->worker.join();delete s;s_=nullptr;return stats;
    }
};
}
