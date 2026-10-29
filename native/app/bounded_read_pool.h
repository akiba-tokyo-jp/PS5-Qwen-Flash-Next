// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <functional>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace qwen_app {
struct BoundedReadRequest {int fd;void*target;std::size_t bytes;std::uint64_t offset;};
// Four existing owned destinations, one producer, at most three persistent
// CPU workers. No GPU access, descriptor changes, retry or allocation per read.
class BoundedReadPool {
    std::function<std::int64_t(const BoundedReadRequest&)> read_;
    std::mutex mutex_;std::condition_variable changed_;
    std::array<std::thread,3> workers_;
    std::array<BoundedReadRequest,4> requests_{};
    std::array<std::int64_t,4> results_{};
    std::array<std::exception_ptr,4> errors_{};
    unsigned ready_=0,started_=0,next_=0,returned_=0,workers_done_=0,depth_=1;
    std::uint64_t epoch_=0;bool stop_=false,pending_=false,failed_=false,uncertain_=false;
    std::atomic<unsigned>active_{0},maximum_{0};
    void lane() noexcept {
        for(;;){std::unique_lock<std::mutex> lock(mutex_);if(next_==4)return;
            const auto index=next_++;const auto request=requests_[index];lock.unlock();
            const auto active=active_.fetch_add(1)+1;auto peak=maximum_.load();
            while(peak<active&&!maximum_.compare_exchange_weak(peak,active)){}
            std::int64_t result=-1;std::exception_ptr error;
            try{result=read_(request);}catch(...){error=std::current_exception();}
            active_.fetch_sub(1);lock.lock();results_[index]=result;errors_[index]=error;++returned_;
        }
    }
    void worker(unsigned index) noexcept {
        std::unique_lock<std::mutex> lock(mutex_);++ready_;changed_.notify_all();std::uint64_t seen=0;
        for(;;){changed_.wait(lock,[&]{return stop_||epoch_!=seen;});if(stop_)return;seen=epoch_;
            if(index>=depth_-1)continue;lock.unlock();lane();lock.lock();++workers_done_;changed_.notify_all();}
    }
public:
    explicit BoundedReadPool(std::function<std::int64_t(const BoundedReadRequest&)>read):read_(std::move(read)){}
    BoundedReadPool(const BoundedReadPool&)=delete;
    void start(){
        std::unique_lock<std::mutex> lock(mutex_);if(started_||stop_||failed_)throw std::logic_error("Fresh read pool required");
        try{for(unsigned i=0;i<3;++i){workers_[i]=std::thread([this,i]{worker(i);});++started_;}}
        catch(...){stop_=true;changed_.notify_all();lock.unlock();for(unsigned i=0;i<started_;++i)if(workers_[i].joinable())workers_[i].join();failed_=true;throw;}
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return ready_==3;})){failed_=uncertain_=true;throw std::runtime_error("Read pool startup completion is unknown; owner retained");}
    }
    std::array<std::int64_t,4> read(const std::array<BoundedReadRequest,4>&requests,unsigned depth){
        if(depth!=1&&depth!=2&&depth!=4)throw std::invalid_argument("Read depth must be 1, 2 or 4");
        for(unsigned i=0;i<4;++i){const auto&r=requests[i];const auto at=reinterpret_cast<std::uintptr_t>(r.target);
            if(r.fd<0||!at||!r.bytes||r.bytes>(2u<<20)||at%16384||r.bytes%16384||r.offset%16384||r.bytes>UINTPTR_MAX-at||r.offset>std::uint64_t(INT64_MAX)-r.bytes)throw std::invalid_argument("Bounded aligned read request required");
            for(unsigned j=0;j<i;++j){const auto other=reinterpret_cast<std::uintptr_t>(requests[j].target);if(at<other+requests[j].bytes&&other<at+r.bytes)throw std::invalid_argument("Read destination leases overlap");}}
        {std::lock_guard<std::mutex> lock(mutex_);if(ready_!=3||stop_||pending_||failed_)throw std::runtime_error("Read pool owner is busy or retained");
            requests_=requests;results_.fill(-1);errors_.fill(nullptr);next_=returned_=workers_done_=0;depth_=depth;maximum_.store(0);pending_=true;++epoch_;changed_.notify_all();}
        lane();std::unique_lock<std::mutex> lock(mutex_);
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return workers_done_==depth_-1;})){failed_=uncertain_=true;throw std::runtime_error("Read completion is unknown; all owners retained");}
        if(returned_!=4||active_.load()){failed_=uncertain_=true;throw std::runtime_error("Read owners did not retire positively");}
        pending_=false;
        for(unsigned i=0;i<4;++i)if(errors_[i]||results_[i]!=std::int64_t(requests_[i].bytes)){failed_=true;if(errors_[i])std::rethrow_exception(errors_[i]);throw std::runtime_error("Bounded read was short");}
        return results_;
    }
    unsigned maximum_inflight()const noexcept{return maximum_.load();}
    void require_completed(){std::lock_guard<std::mutex> lock(mutex_);if(pending_||uncertain_||active_.load())throw std::runtime_error("Read pool has an outstanding owner");}
    void stop_completed(){std::unique_lock<std::mutex> lock(mutex_);if(pending_||uncertain_||active_.load())throw std::runtime_error("Uncertain read owners must remain alive");stop_=true;changed_.notify_all();lock.unlock();for(unsigned i=0;i<started_;++i)if(workers_[i].joinable())workers_[i].join();}
};
}
