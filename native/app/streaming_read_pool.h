// SPDX-License-Identifier: MIT
#pragma once
#include "bounded_read_pool.h"
#include <algorithm>

namespace qwen_app {
// Four fixed CPU leases. The original producer consumes each positive result
// before reusing that lane; workers never access the GPU or modify descriptors.
class StreamingReadPool {
    enum class State {idle,queued,reading,ready};
    struct Slot {State state=State::idle;BoundedReadRequest request{};unsigned id=0;std::int64_t result=-1;std::exception_ptr error;std::uint64_t order=0,queued_ns=0,ready_ns=0;};
    std::function<std::int64_t(const BoundedReadRequest&)>reader_;
    std::array<std::thread,4>threads_;
    std::array<Slot,4>slots_{};
    std::mutex mutex_;std::condition_variable changed_;
    unsigned started_=0,ready_=0,active_=0,maximum_=0;
    std::uint64_t order_=0;bool stop_=false,pending_=false,failed_=false,uncertain_=false;
    std::array<std::uint64_t,4>legacy_timing_{};
    std::array<std::uint64_t,16>delivery_{};
    std::uint64_t occupancy_at_=0;
    static std::uint64_t now_ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
    void occupancy(std::uint64_t now){if(occupancy_at_)delivery_[8+active_]+=now-occupancy_at_;occupancy_at_=now;}
    void worker(unsigned lane)noexcept{
        std::unique_lock<std::mutex>lock(mutex_);++ready_;changed_.notify_all();
        for(;;){changed_.wait(lock,[&]{return stop_||slots_[lane].state==State::queued;});if(stop_)return;
            auto&s=slots_[lane];const auto r=s.request;const auto begin=now_ns();delivery_[3]+=begin-s.queued_ns;occupancy(begin);s.state=State::reading;++active_;maximum_=std::max(maximum_,active_);lock.unlock();
            std::int64_t got=-1;std::exception_ptr error;try{got=reader_(r);}catch(...){error=std::current_exception();}
            const auto returned=now_ns();lock.lock();occupancy(now_ns());--active_;delivery_[4]+=returned-begin;++delivery_[2];if(error||got!=std::int64_t(r.bytes))++delivery_[13];s.ready_ns=returned;s.result=got;s.error=error;s.order=++order_;s.state=State::ready;changed_.notify_all();
        }
    }
public:
    explicit StreamingReadPool(std::function<std::int64_t(const BoundedReadRequest&)>reader):reader_(std::move(reader)){}
    void start(){
        std::unique_lock<std::mutex>lock(mutex_);if(started_||stop_||failed_)throw std::logic_error("Fresh streaming owner required");
        try{for(unsigned i=0;i<4;++i){threads_[i]=std::thread([this,i]{worker(i);});++started_;}}
        catch(...){stop_=true;changed_.notify_all();lock.unlock();for(unsigned i=0;i<started_;++i)threads_[i].join();failed_=true;throw;}
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return ready_==4;})){failed_=uncertain_=true;throw std::runtime_error("Streaming startup completion unknown; retain owner");}
    }
    template<class Before,class Consume>void run(const BoundedReadRequest*requests,unsigned count,const std::array<void*,4>&leases,Before before,Consume consume){
        if(!requests||!count||count>12)throw std::invalid_argument("One to twelve known owned requests required");
        for(unsigned i=0;i<4;++i){const auto at=reinterpret_cast<std::uintptr_t>(leases[i]);if(!at||at%16384||at>UINTPTR_MAX-(2u<<20))throw std::invalid_argument("Aligned streaming lease required");
            for(unsigned j=0;j<i;++j){const auto other=reinterpret_cast<std::uintptr_t>(leases[j]);if(at<other+(2u<<20)&&other<at+(2u<<20))throw std::invalid_argument("Streaming leases overlap");}}
        for(unsigned i=0;i<count;++i){const auto&r=requests[i];if(r.fd<0||!r.bytes||r.bytes>(2u<<20)||r.bytes%16384||r.offset%16384||r.offset>std::uint64_t(INT64_MAX)-r.bytes)
            throw std::invalid_argument("Bounded aligned streaming extent required");}
        std::unique_lock<std::mutex>lock(mutex_);if(ready_!=4||pending_||failed_||stop_||active_)throw std::runtime_error("Streaming owner unavailable");
        for(const auto&s:slots_)if(s.state!=State::idle)throw std::runtime_error("A streaming lease remains live");
        pending_=true;maximum_=0;const auto run_started=now_ns();occupancy_at_=run_started;++delivery_[0];unsigned next=0,live=0,completed=0;std::exception_ptr failure;
        const auto queue=[&](unsigned lane){
            const auto before_started=now_ns();lock.unlock();try{before(next);}catch(...){failure=std::current_exception();}lock.lock();delivery_[14]+=now_ns()-before_started;if(failure)return;
            auto&s=slots_[lane];s.request=requests[next];s.request.target=leases[lane];s.id=next++;s.result=-1;s.error=nullptr;s.queued_ns=now_ns();s.state=State::queued;++delivery_[1];++live;changed_.notify_all();
        };
        for(unsigned i=0;i<4&&next<count&&!failure;++i)queue(i);
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(10);
        while(live){
            if(!changed_.wait_until(lock,deadline,[&]{return std::any_of(slots_.begin(),slots_.end(),[](const auto&s){return s.state==State::ready;});})){
                failed_=uncertain_=true;throw std::runtime_error("Streaming read completion unknown; retain all leases");}
            unsigned lane=4;for(unsigned i=0;i<4;++i)if(slots_[i].state==State::ready&&(lane==4||slots_[i].order<slots_[lane].order))lane=i;
            auto&s=slots_[lane];const auto id=s.id;const auto request=s.request;const auto got=s.result;const auto error=s.error;
            delivery_[5]+=now_ns()-s.ready_ns;
            if(!failure){if(error)failure=error;else if(got!=std::int64_t(request.bytes))failure=std::make_exception_ptr(std::runtime_error("Streaming read was short"));
                else{const auto consume_started=now_ns();lock.unlock();try{consume(id,request.target,got);}catch(...){failure=std::current_exception();}lock.lock();delivery_[6]+=now_ns()-consume_started;}}
            s.state=State::idle;--live;++completed;if(!failure&&next<count)queue(lane);
        }
        if(active_){failed_=uncertain_=true;throw std::runtime_error("Streaming worker retirement unknown");}
        const auto run_finished=now_ns();occupancy(run_finished);occupancy_at_=0;delivery_[7]+=run_finished-run_started;
        pending_=false;if(failure){++delivery_[15];failed_=true;lock.unlock();std::rethrow_exception(failure);}
        if(completed!=count||next!=count){failed_=true;throw std::runtime_error("Streaming request accounting differs");}
    }
    unsigned maximum_inflight(){std::lock_guard<std::mutex>lock(mutex_);return maximum_;}
    std::array<std::uint64_t,16>delivery_timing(){require_completed();std::lock_guard<std::mutex>lock(mutex_);return delivery_;}
    std::array<std::int64_t,4>read(const std::array<BoundedReadRequest,4>&requests,unsigned depth){
        if(depth!=4)throw std::invalid_argument("Legacy streaming compatibility owns four lanes");
        std::array<void*,4>leases{};for(unsigned i=0;i<4;++i)leases[i]=requests[i].target;
        std::array<std::int64_t,4>results{};const auto start=std::chrono::steady_clock::now();
        run(requests.data(),4,leases,[](unsigned){},[&](unsigned id,const void*,std::int64_t got){results[id]=got;});
        ++legacy_timing_[0];legacy_timing_[2]+=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();return results;
    }
    void timing(std::uint64_t*out){require_completed();std::copy(legacy_timing_.begin(),legacy_timing_.end(),out);}
    void require_completed(){std::lock_guard<std::mutex>lock(mutex_);if(pending_||uncertain_||active_)throw std::runtime_error("Streaming lease is outstanding");for(const auto&s:slots_)if(s.state!=State::idle)throw std::runtime_error("Streaming slot is outstanding");}
    void stop_completed(){require_completed();std::unique_lock<std::mutex>lock(mutex_);stop_=true;changed_.notify_all();lock.unlock();for(unsigned i=0;i<started_;++i)if(threads_[i].joinable())threads_[i].join();}
};
}
