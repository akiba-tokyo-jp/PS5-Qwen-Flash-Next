// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace qwen_app {
struct CompletionRead {
    int fd=-1;
    void *target=nullptr;
    std::uint64_t bytes=0,offset=0,id=0;
};
// Two fixed workers; completed buffers remain owned until explicit release.
// The caller performs memory admission and retains the object after uncertainty.
class CompletionSourceIO {
public:
    using Reader=std::int64_t (*)(void *,unsigned,const CompletionRead &);
    struct Result {unsigned slot;CompletionRead request;std::int64_t bytes;};
private:
    enum class State {idle,queued,reading,ready,held};
    struct Slot {State state=State::idle;CompletionRead request{};std::int64_t result=-1;std::uint64_t order=0;};
    std::array<Slot,2> slots_{};
    std::array<std::thread,2> workers_;
    std::mutex mutex_;
    std::condition_variable changed_;
    Reader read_;
    void *context_;
    unsigned ready_=0;
    std::uint64_t completion_order_=0;
    bool started_=false,stop_=false,uncertain_=false,failed_=false;
    void worker(unsigned index) noexcept {
        std::unique_lock<std::mutex> lock(mutex_);++ready_;changed_.notify_all();
        for(;;) {
            changed_.wait(lock,[&]{return stop_||slots_[index].state==State::queued;});
            if(stop_)return;
            auto &slot=slots_[index];const auto request=slot.request;slot.state=State::reading;lock.unlock();
            std::int64_t result=-1;bool threw=false;
            try{result=read_(context_,index,request);}catch(...){threw=true;}
            lock.lock();slot.result=result;slot.order=++completion_order_;slot.state=State::ready;
            // A thrown native reader may have lost completion evidence.
            if(threw)uncertain_=failed_=true;
            if(result<0||static_cast<std::uint64_t>(result)!=request.bytes)failed_=true;
            changed_.notify_all();
        }
    }
public:
    CompletionSourceIO(Reader reader,void *context):read_(reader),context_(context) {
        if(!reader)throw std::invalid_argument("A read operation is required");
    }
    CompletionSourceIO(const CompletionSourceIO &)=delete;
    CompletionSourceIO &operator=(const CompletionSourceIO &)=delete;
    ~CompletionSourceIO()=default;
    void start() {
        std::unique_lock<std::mutex> lock(mutex_);
        if(started_||stop_)throw std::logic_error("A fresh completion queue is required");
        started_=true;
        try{for(unsigned i=0;i<2;++i)workers_[i]=std::thread([this,i]{worker(i);});}
        catch(...){uncertain_=failed_=true;throw;}
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return ready_==2;})) {
            uncertain_=failed_=true;throw std::runtime_error("Source startup is uncertain; backing retained");
        }
    }
    void submit(unsigned index,const CompletionRead &request) {
        const auto at=reinterpret_cast<std::uintptr_t>(request.target);
        if(index>=2||request.fd<0||!at||!request.bytes||request.bytes>(4u<<20)||
           at%16384||request.bytes%16384||request.offset%16384||request.bytes>UINTPTR_MAX-at||
           request.offset>INT64_MAX-request.bytes)
            throw std::invalid_argument("A bounded aligned request is required");
        std::lock_guard<std::mutex> lock(mutex_);
        if(ready_!=2||stop_||failed_||slots_[index].state!=State::idle)
            throw std::logic_error("The source slot is unavailable");
        const auto &other=slots_[1-index];
        if(other.state!=State::idle) {
            const auto b=reinterpret_cast<std::uintptr_t>(other.request.target);
            if(at<b+other.request.bytes&&b<at+request.bytes)
                throw std::invalid_argument("Live source destinations must be disjoint");
        }
        slots_[index].request=request;slots_[index].result=-1;slots_[index].state=State::queued;changed_.notify_all();
    }
    // Pair-wave control waits for both live reads. Continuous delivery takes
    // the first positive completion, without releasing or reusing its buffer.
    Result take(bool wait_all) {
        std::unique_lock<std::mutex> lock(mutex_);
        auto available=[&] {
            bool found=false;
            for(const auto &s:slots_) {
                if(s.state==State::ready)found=true;
                if(wait_all&&(s.state==State::queued||s.state==State::reading))return false;
            }
            return found;
        };
        bool live=false;for(const auto &s:slots_)live|=s.state!=State::idle;
        if(!live||stop_||uncertain_)throw std::logic_error("No known source completion is available");
        if(!changed_.wait_for(lock,std::chrono::seconds(10),available)) {
            uncertain_=failed_=true;throw std::runtime_error("Source completion is uncertain; backing retained");
        }
        if(uncertain_)throw std::runtime_error("Source completion evidence was lost");
        unsigned index=2;
        for(unsigned i=0;i<2;++i)if(slots_[i].state==State::ready&&
            (index==2||slots_[i].order<slots_[index].order))index=i;
        auto &s=slots_[index];s.state=State::held;return {index,s.request,s.result};
    }
    void release(unsigned index) {
        std::lock_guard<std::mutex> lock(mutex_);
        if(index>=2||slots_[index].state!=State::held||uncertain_)
            throw std::logic_error("Only a completed held buffer can be released");
        slots_[index].state=State::idle;
    }
    void stop_completed() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(ready_!=2||stop_||uncertain_)throw std::logic_error("Source shutdown is not admitted");
            for(const auto &s:slots_)if(s.state!=State::idle)throw std::logic_error("A source lease is still held");
            stop_=true;changed_.notify_all();
        }
        for(auto &t:workers_)t.join();
    }
};
}
