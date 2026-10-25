// SPDX-License-Identifier: MIT
#pragma once
#include "mapped_source.h"
#include <condition_variable>
#include <exception>
#include <mutex>

namespace qwen_app {
// Experimental CPU executor. The caller owns every descriptor and the complete
// 8 MiB payload window. Keep the object alive after any uncertain completion.
// No GPU operation, file open/close, allocation or retry occurs in read().
class QueuedSourceIO {
    SourceReadOps & ops_;
    std::mutex mutex_;
    std::condition_variable changed_;
    std::array<std::thread,3> workers_;
    std::array<SourceReadRequest,4> requests_{};
    std::array<std::int64_t,4> results_{};
    std::array<std::exception_ptr,4> errors_{};
    std::uint64_t generation_=0;
    unsigned ready_=0,count_=0,completed_=0;
    bool stop_=false,failed_=false,uncertain_=false;
    void worker(unsigned index) noexcept {
        std::unique_lock<std::mutex> lock(mutex_);
        ++ready_;changed_.notify_all();std::uint64_t seen=0;
        for(;;) {
            changed_.wait(lock,[&]{return stop_ || generation_!=seen;});
            if(stop_)return;
            seen=generation_;
            if(index>=count_)continue;
            const auto request=requests_[index];lock.unlock();
            std::int64_t result=-1;std::exception_ptr error;
            try { result=ops_.read_at(request.fd,request.target,request.bytes,request.offset); }
            catch(...) { error=std::current_exception(); }
            lock.lock();results_[index]=result;errors_[index]=error;++completed_;changed_.notify_all();
        }
    }
public:
    explicit QueuedSourceIO(SourceReadOps & ops):ops_(ops){}
    QueuedSourceIO(const QueuedSourceIO &)=delete;
    QueuedSourceIO & operator=(const QueuedSourceIO &)=delete;
    ~QueuedSourceIO()=default;
    void start() {
        std::unique_lock<std::mutex> lock(mutex_);
        if(ready_ || failed_ || stop_)throw std::logic_error("A fresh queued source owner is required");
        try { for(unsigned i=0;i<3;++i)workers_[i]=std::thread([this,i]{worker(i+1);}); }
        catch(...) { failed_=true;throw; }
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return ready_==3;})) {
            failed_=uncertain_=true;throw std::runtime_error("Queued source startup is uncertain; owner retained");
        }
    }
    std::array<std::int64_t,4> read(const std::array<SourceReadRequest,4> & requests,unsigned count) {
        if(count!=2 && count!=4)throw std::invalid_argument("Only two or four CPU source reads are admitted");
        for(unsigned i=0;i<count;++i) {
            const auto & r=requests[i];const auto at=reinterpret_cast<std::uintptr_t>(r.target);
            if(r.fd<0 || !at || !r.bytes || r.bytes>model_read_window/count ||
               at%model_read_alignment || r.bytes%model_read_alignment || r.offset%model_read_alignment ||
               r.bytes>UINTPTR_MAX-at)throw std::invalid_argument("Queued source read escaped its aligned owned window");
            for(unsigned j=0;j<i;++j) {
                const auto other=reinterpret_cast<std::uintptr_t>(requests[j].target);
                if(at<other+requests[j].bytes && other<at+r.bytes)
                    throw std::invalid_argument("Queued source destinations must be disjoint");
            }
        }
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(ready_!=3 || stop_ || failed_ || completed_!=count_ || generation_==UINT64_MAX)
                throw std::runtime_error("Queued source owner is busy or quarantined");
            requests_=requests;count_=count;completed_=0;results_.fill(-1);errors_.fill(nullptr);
            ++generation_;changed_.notify_all();
        }
        std::int64_t result=-1;std::exception_ptr error;
        try { result=ops_.read_at(requests[0].fd,requests[0].target,requests[0].bytes,requests[0].offset); }
        catch(...) { error=std::current_exception(); }
        std::unique_lock<std::mutex> lock(mutex_);
        results_[0]=result;errors_[0]=error;++completed_;
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return completed_==count_;})) {
            failed_=uncertain_=true;throw std::runtime_error("Queued source completion is uncertain; backing retained");
        }
        for(unsigned i=0;i<count;++i)if(errors_[i]) {failed_=true;std::rethrow_exception(errors_[i]);}
        return results_;
    }
    void stop_completed() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(uncertain_ || completed_!=count_ || ready_!=3 || stop_)
                throw std::runtime_error("Queued source shutdown requires known completion");
            stop_=true;changed_.notify_all();
        }
        for(auto & worker:workers_)if(worker.joinable())worker.join();
    }
};
}
