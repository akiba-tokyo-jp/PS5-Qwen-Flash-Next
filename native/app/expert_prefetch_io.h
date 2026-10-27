// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <chrono>
#include <condition_variable>
#include <exception>
#include <functional>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace qwen_app {
// A single persistent CPU worker. A timed-out opaque read is never cancelled:
// its job, actual allocation leases and worker remain retained together.
class ExpertPrefetchIO {
    struct State {
        std::mutex mutex;
        std::condition_variable changed;
        std::function<void()> job;
        std::exception_ptr error;
        std::thread worker;
        bool pending=false,done=true,stop=false,quarantined=false;
    };
    State *state_=nullptr;
    std::thread::id owner_=std::this_thread::get_id();
    void owner()const {
        if(owner_!=std::this_thread::get_id()||!state_)
            throw std::runtime_error("Expert prefetch requires its original live producer");
    }
public:
    ExpertPrefetchIO() {
        auto *s=new State;
        try {s->worker=std::thread([s] {
            std::unique_lock<std::mutex> lock(s->mutex);
            for(;;) {
                s->changed.wait(lock,[&]{return s->pending||s->stop;});
                if(s->stop)return;
                // Keep the job (and its leases) until the producer observes
                // positive completion. Never clear it on the worker thread.
                lock.unlock();std::exception_ptr error;
                try{s->job();}catch(...){error=std::current_exception();}
                lock.lock();s->error=error;s->pending=false;s->done=true;s->changed.notify_all();
            }
        });}catch(...){delete s;throw;}
        state_=s;
    }
    ExpertPrefetchIO(const ExpertPrefetchIO&)=delete;
    ExpertPrefetchIO&operator=(const ExpertPrefetchIO&)=delete;
    ~ExpertPrefetchIO() {
        if(!state_)return;
        // Normal owners close explicitly. Destruction after uncertainty keeps
        // the entire state graph alive for ordinary process shutdown.
        auto *s=state_;std::unique_lock<std::mutex> lock(s->mutex);
        if(!s->done||s->quarantined)return;
        s->stop=true;s->changed.notify_all();lock.unlock();
        s->worker.join();delete s;
    }
    void submit(std::function<void()> job) {
        owner();auto &s=*state_;std::lock_guard<std::mutex> lock(s.mutex);
        if(!job||s.pending||!s.done||s.job||s.quarantined||s.stop)
            throw std::runtime_error("Only one completed-owner expert prefetch job is permitted");
        s.job=std::move(job);s.error=nullptr;s.done=false;s.pending=true;s.changed.notify_all();
    }
    void complete(std::chrono::milliseconds timeout=std::chrono::seconds(10)) {
        owner();auto &s=*state_;std::unique_lock<std::mutex> lock(s.mutex);
        if(timeout.count()<=0||timeout>std::chrono::seconds(10))
            throw std::invalid_argument("Expert prefetch wait must remain positively bounded");
        if(s.quarantined)throw std::runtime_error("Expert prefetch completion is quarantined; leases retained");
        if(!s.changed.wait_for(lock,timeout,[&]{return s.done;})) {
            s.quarantined=true;
            throw std::runtime_error("Expert prefetch read completion is unknown; leases retained");
        }
        if(s.error){s.quarantined=true;std::rethrow_exception(s.error);}
        s.job={};
    }
    void close_completed() {
        complete();auto *s=state_;std::unique_lock<std::mutex> lock(s->mutex);
        s->stop=true;s->changed.notify_all();lock.unlock();s->worker.join();delete s;state_=nullptr;
    }
};
struct ExpertPrefetchDestination {
    void *data=nullptr;
    std::size_t bytes=0,alignment=0;
    // Aliases the actual shared Vulkan allocation; no imported CPU pointer.
    std::shared_ptr<void> backing;
};
}
