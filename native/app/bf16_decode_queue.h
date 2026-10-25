// SPDX-License-Identifier: MIT
#pragma once
#include "bf16_lossless.h"
#include <array>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace qwen_app {
// Three fixed workers plus the caller. Payload stays in the caller's existing
// input/output/scratch window. Unknown completion retains the queue and window.
class BF16DecodeQueue {
    std::mutex mutex_;
    std::condition_variable changed_;
    std::array<std::thread,3> workers_;
    qwen_bf16_decode_plan plan_{};
    unsigned ready_=0,completed_=0;
    uint64_t generation_=0;
    bool stop_=false,pending_=false,failed_=false,uncertain_=false;
    std::array<int,4> results_{};
    void worker(unsigned index) noexcept {
        std::unique_lock<std::mutex> lock(mutex_);++ready_;changed_.notify_all();uint64_t seen=0;
        for(;;) {
            changed_.wait(lock,[&]{return stop_||generation_!=seen;});if(stop_)return;
            seen=generation_;const auto plan=plan_;lock.unlock();
            const int result=qwen_bf16_decode_shard(&plan,index);lock.lock();
            results_[index]=result;++completed_;changed_.notify_all();
        }
    }
public:
    BF16DecodeQueue()=default;
    BF16DecodeQueue(const BF16DecodeQueue &)=delete;
    BF16DecodeQueue &operator=(const BF16DecodeQueue &)=delete;
    ~BF16DecodeQueue()=default;
    void start() {
        std::unique_lock<std::mutex> lock(mutex_);
        if(ready_||stop_||failed_)throw std::logic_error("A fresh decode queue is required");
        try{for(unsigned i=0;i<3;++i)workers_[i]=std::thread([this,i]{worker(i+1);});}
        catch(...){failed_=true;throw;}
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return ready_==3;})) {
            failed_=uncertain_=true;throw std::runtime_error("Decode worker startup is uncertain");
        }
    }
    bool decode(const qwen_bf16_decode_plan &plan) {
        if(plan.shards!=4||plan.codec!=QWEN_BF16_CODEC_EXPONENT)throw std::invalid_argument("Four original exponent shards are required");
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(ready_!=3||stop_||failed_||pending_)throw std::logic_error("Decode queue is unavailable");
            plan_=plan;results_.fill(0);completed_=0;pending_=true;++generation_;changed_.notify_all();
        }
        const int own=qwen_bf16_decode_shard(&plan,0);
        std::unique_lock<std::mutex> lock(mutex_);results_[0]=own;
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return completed_==3;})) {
            failed_=uncertain_=true;throw std::runtime_error("Decode completion is uncertain; backing retained");
        }
        pending_=false;for(const auto result:results_)if(!result){failed_=true;return false;}
        return true;
    }
    void stop_completed() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(uncertain_||pending_||ready_!=3||stop_)throw std::logic_error("Decode workers have not positively completed");
            stop_=true;changed_.notify_all();
        }
        for(auto &worker:workers_)worker.join();
    }
};
}
