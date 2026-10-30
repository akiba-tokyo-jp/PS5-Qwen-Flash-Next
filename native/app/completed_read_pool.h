// SPDX-License-Identifier: MIT
#pragma once
#include "bounded_read_pool.h"

namespace qwen_app {
// Four CPU readers; callbacks execute only on the original producer. Existing
// destination leases remain pinned until every read and callback has returned.
class CompletedReadPool {
    std::function<std::int64_t(const BoundedReadRequest&)> read_;
    std::mutex mutex_;std::condition_variable changed_;
    std::array<std::thread,4> workers_;
    std::array<BoundedReadRequest,4> requests_{};
    std::array<std::int64_t,4> results_{};
    std::array<std::exception_ptr,4> errors_{};
    std::array<unsigned,4> order_{};
    unsigned ready_=0,started_=0,returned_=0;
    std::uint64_t epoch_=0;bool stop_=false,pending_=false,failed_=false,uncertain_=false;
    std::atomic<unsigned>active_{0},maximum_{0};
    void worker(unsigned i)noexcept {
        std::unique_lock<std::mutex>lock(mutex_);++ready_;changed_.notify_all();std::uint64_t seen=0;
        for(;;){changed_.wait(lock,[&]{return stop_||epoch_!=seen;});if(stop_)return;
            seen=epoch_;const auto request=requests_[i];lock.unlock();
            const auto n=active_.fetch_add(1)+1;auto peak=maximum_.load();
            while(peak<n&&!maximum_.compare_exchange_weak(peak,n)){}
            std::int64_t got=-1;std::exception_ptr error;
            try{got=read_(request);}catch(...){error=std::current_exception();}
            active_.fetch_sub(1);lock.lock();results_[i]=got;errors_[i]=error;order_[returned_++]=i;changed_.notify_all();
        }
    }
public:
    explicit CompletedReadPool(std::function<std::int64_t(const BoundedReadRequest&)>read):read_(std::move(read)){}
    CompletedReadPool(const CompletedReadPool&)=delete;
    void start(){
        std::unique_lock<std::mutex>lock(mutex_);if(started_||stop_||failed_)throw std::logic_error("Fresh completed-read pool required");
        try{for(unsigned i=0;i<4;++i){workers_[i]=std::thread([this,i]{worker(i);});++started_;}}
        catch(...){stop_=true;changed_.notify_all();lock.unlock();for(unsigned i=0;i<started_;++i)if(workers_[i].joinable())workers_[i].join();failed_=true;throw;}
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return ready_==4;})){failed_=uncertain_=true;throw std::runtime_error("Reader startup unknown; retain owner");}
    }
    template<class Consume>std::array<std::int64_t,4>read_each(const std::array<BoundedReadRequest,4>&requests,Consume&&consume){
        for(unsigned i=0;i<4;++i){const auto&r=requests[i];const auto at=reinterpret_cast<std::uintptr_t>(r.target);
            if(r.fd<0||!at||!r.bytes||r.bytes>(2u<<20)||at%16384||r.bytes%16384||r.offset%16384||r.bytes>UINTPTR_MAX-at||r.offset>std::uint64_t(INT64_MAX)-r.bytes)
                throw std::invalid_argument("Completed reads require bounded aligned leases");
            for(unsigned j=0;j<i;++j){const auto other=reinterpret_cast<std::uintptr_t>(requests[j].target);if(at<other+requests[j].bytes&&other<at+r.bytes)throw std::invalid_argument("Read destinations overlap");}}
        std::unique_lock<std::mutex>lock(mutex_);
        if(ready_!=4||pending_||failed_||stop_)throw std::runtime_error("Completed-read owner is unavailable");
        requests_=requests;results_.fill(-1);errors_.fill(nullptr);returned_=0;maximum_.store(0);pending_=true;++epoch_;changed_.notify_all();
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);std::exception_ptr failure;
        for(unsigned delivered=0;delivered<4;++delivered){
            if(!changed_.wait_until(lock,deadline,[&]{return returned_>delivered;})){failed_=uncertain_=true;throw std::runtime_error("Read completion unknown; retain all leases");}
            const auto i=order_[delivered];const auto got=results_[i];
            if(!failure){
                if(errors_[i])failure=errors_[i];
                else if(got!=std::int64_t(requests_[i].bytes))failure=std::make_exception_ptr(std::runtime_error("Completed read was short"));
                else{lock.unlock();try{consume(i,got);}catch(...){failure=std::current_exception();}lock.lock();}
            }
        }
        if(active_.load()){failed_=uncertain_=true;throw std::runtime_error("Read completion retained an active worker");}
        pending_=false;const auto result=results_;
        if(failure){failed_=true;lock.unlock();std::rethrow_exception(failure);}return result;
    }
    unsigned maximum_inflight()const noexcept{return maximum_.load();}
    unsigned inflight()const noexcept{return active_.load();}
    std::array<std::int64_t,4>read(const std::array<BoundedReadRequest,4>&requests,unsigned depth){
        if(depth!=4)throw std::invalid_argument("This pool owns exactly four read lanes");
        return read_each(requests,[](unsigned,std::int64_t){});
    }
    void require_completed(){std::lock_guard<std::mutex>lock(mutex_);if(pending_||uncertain_||active_.load())throw std::runtime_error("Completed-read lease is outstanding");}
    void stop_completed(){std::unique_lock<std::mutex>lock(mutex_);if(pending_||uncertain_||active_.load())throw std::runtime_error("Uncertain read leases must remain alive");stop_=true;changed_.notify_all();lock.unlock();for(unsigned i=0;i<started_;++i)if(workers_[i].joinable())workers_[i].join();}
};
}
