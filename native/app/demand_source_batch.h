// SPDX-License-Identifier: MIT
#pragma once
#include "completion_source_io.h"

namespace qwen_app {
// One persistent I/O worker plus the caller, matching the production thread
// count. Both lanes take the next known request without a pair barrier.
// Requests and results belong to this retained owner, never a caller's stack.
class DemandSourceBatch {
public:
    using Reader=std::int64_t (*)(void *,const CompletionRead &);
    static constexpr unsigned maximum=40;
private:
    Reader reader_;void *context_;
    std::array<CompletionRead,maximum> requests_{};
    std::array<std::int64_t,maximum> results_{};
    std::thread worker_;
    std::mutex mutex_;
    std::condition_variable changed_;
    unsigned count_=0,next_=0,returned_=0;
    bool ready_=false,pending_=false,completed_=true,stop_=false,failed_=false,uncertain_=false;
    void lane() noexcept {
        for(;;) {
            std::unique_lock<std::mutex> lock(mutex_);
            if(next_==count_||failed_)return;
            const unsigned index=next_++;const auto request=requests_[index];lock.unlock();
            std::int64_t result=-1;bool threw=false;
            try{result=reader_(context_,request);}catch(...){threw=true;}
            lock.lock();results_[index]=result;++returned_;
            if(threw)failed_=uncertain_=true;
            if(result!=static_cast<std::int64_t>(request.bytes))failed_=true;
        }
    }
    void run() noexcept {
        std::unique_lock<std::mutex> lock(mutex_);ready_=true;changed_.notify_all();
        for(;;) {
            changed_.wait(lock,[&]{return pending_||stop_;});if(stop_)return;
            lock.unlock();lane();lock.lock();pending_=false;completed_=true;changed_.notify_all();
        }
    }
public:
    DemandSourceBatch(Reader reader,void *context):reader_(reader),context_(context) {
        if(!reader_)throw std::invalid_argument("A known-demand reader is required");
    }
    DemandSourceBatch(const DemandSourceBatch &)=delete;
    DemandSourceBatch &operator=(const DemandSourceBatch &)=delete;
    ~DemandSourceBatch()=default;
    void start() {
        std::unique_lock<std::mutex> lock(mutex_);
        if(ready_||worker_.joinable()||stop_||failed_)throw std::logic_error("A fresh demand worker is required");
        worker_=std::thread([this]{run();});
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return ready_;})) {
            failed_=uncertain_=true;throw std::runtime_error("Demand worker startup is uncertain; owner retained");
        }
    }
    void read(const CompletionRead *requests,unsigned count) {
        if(!requests||!count||count>maximum)throw std::invalid_argument("The known-demand batch exceeds its bound");
        for(unsigned i=0;i<count;++i) {
            const auto &r=requests[i];const auto at=reinterpret_cast<std::uintptr_t>(r.target);
            if(r.fd<0||!at||!r.bytes||r.bytes>(4u<<20)||at%16384||r.bytes%16384||r.offset%16384||
               r.bytes>UINTPTR_MAX-at||r.offset>INT64_MAX-r.bytes)
                throw std::invalid_argument("Demand reads require exact bounded aligned extents");
            for(unsigned j=0;j<i;++j) {
                const auto b=reinterpret_cast<std::uintptr_t>(requests[j].target);
                if(at<b+requests[j].bytes&&b<at+r.bytes)
                    throw std::invalid_argument("Known-demand destinations overlap");
            }
        }
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(!ready_||stop_||failed_||pending_||!completed_)throw std::logic_error("The demand owner is busy or quarantined");
            for(unsigned i=0;i<count;++i){requests_[i]=requests[i];results_[i]=-1;}
            count_=count;next_=returned_=0;completed_=false;pending_=true;changed_.notify_all();
        }
        lane();
        std::unique_lock<std::mutex> lock(mutex_);
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return completed_;})) {
            failed_=uncertain_=true;throw std::runtime_error("Demand completion is uncertain; backing retained");
        }
        if(uncertain_||failed_||returned_!=count_)
            throw std::runtime_error("The complete known-demand batch did not return exact bytes");
    }
    void require_completed() {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!ready_||stop_||failed_||uncertain_||pending_||!completed_||!worker_.joinable())
            throw std::logic_error("A healthy idle demand worker is required");
    }
    bool completion_known() {
        std::lock_guard<std::mutex> lock(mutex_);
        return ready_&&!uncertain_&&!pending_&&completed_&&worker_.joinable()&&!stop_;
    }
    void stop_completed() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(!ready_||stop_||uncertain_||pending_||!completed_||!worker_.joinable())
                throw std::logic_error("Demand shutdown requires positive completion");
            stop_=true;changed_.notify_all();
        }
        worker_.join();
    }
};
}
