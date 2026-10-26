// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <mutex>
#include <stdexcept>
#include <thread>

namespace qwen_app {
struct VectorDestination { void *data=nullptr;std::uint32_t bytes=0; };
struct VectoredRead {
    int fd=-1;
    std::uint64_t device=0,inode=0,file_bytes=0,offset=0,id=0;
    unsigned count=0;
    std::array<VectorDestination,3> destinations{};
    std::uint64_t bytes() const {
        std::uint64_t total=0;
        for(unsigned i=0;i<count&&i<destinations.size();++i)total+=destinations[i].bytes;
        return total;
    }
};
// Experimental owner for at most two real I/O calls, each with one or three
// destinations. Every actual byte is charged and every destination is checked.
// The caller must retain descriptor and destination leases through completion.
class VectoredSourceBatch {
public:
    using Reader=std::int64_t (*)(void *,const VectoredRead &);
private:
    Reader reader_;void *context_;
    std::array<VectoredRead,2> requests_{};
    std::thread worker_;std::thread::id producer_;
    std::mutex mutex_;std::condition_variable changed_;
    bool ready_=false,pending_=false,worker_done_=true,caller_done_=true;
    bool stop_=false,failed_=false,uncertain_=false;
    void run() noexcept {
        std::unique_lock<std::mutex> lock(mutex_);ready_=true;changed_.notify_all();
        for(;;) {
            changed_.wait(lock,[&]{return pending_||stop_;});if(stop_)return;
            const auto request=requests_[1];lock.unlock();
            std::int64_t result=-1;bool threw=false;
            try{result=reader_(context_,request);}catch(...){threw=true;}
            lock.lock();worker_done_=true;pending_=false;
            if(threw)failed_=uncertain_=true;
            if(result!=static_cast<std::int64_t>(request.bytes()))failed_=true;
            changed_.notify_all();
        }
    }
    void owner() const {
        if(producer_!=std::this_thread::get_id())throw std::logic_error("Vector I/O requires its original producer");
    }
    static void validate(const VectoredRead *requests,unsigned count) {
        if(!requests||!count||count>2)throw std::invalid_argument("Vector I/O permits one or two calls");
        for(unsigned i=0;i<count;++i) {
            const auto &r=requests[i];
            if(r.fd<0||!r.device||!r.inode||!r.file_bytes||r.file_bytes>(512ull<<20)||
               (r.count!=1&&r.count!=3)||r.offset%16384||!r.id)
                throw std::invalid_argument("Vector source identity or shape is invalid");
            const auto bytes=r.bytes();
            if(!bytes||bytes>(12u<<20)||r.offset>r.file_bytes||bytes>r.file_bytes-r.offset)
                throw std::invalid_argument("Vector source exceeds its sealed physical file");
            for(unsigned j=0;j<r.count;++j) {
                const auto &v=r.destinations[j];const auto at=reinterpret_cast<std::uintptr_t>(v.data);
                if(!at||at%16384||!v.bytes||v.bytes>(4u<<20)||v.bytes%16384||v.bytes>UINTPTR_MAX-at)
                    throw std::invalid_argument("Vector destination exceeds its aligned owned extent");
                for(unsigned a=0;a<=i;++a)for(unsigned b=0;b<(a==i?j:requests[a].count);++b) {
                    const auto &other=requests[a].destinations[b];const auto start=reinterpret_cast<std::uintptr_t>(other.data);
                    if(at<start+other.bytes&&start<at+v.bytes)
                        throw std::invalid_argument("Vector destinations overlap");
                }
            }
        }
        if(count==2) {
            const auto &a=requests[0];const auto &b=requests[1];
            if(a.id==b.id||a.device!=b.device)throw std::invalid_argument("Vector pair has no distinct same-device leases");
            if((a.fd==b.fd&&a.inode!=b.inode)||(a.inode==b.inode&&a.file_bytes!=b.file_bytes))
                throw std::invalid_argument("Vector descriptor aliases have inconsistent source identity");
            if(a.inode==b.inode) {
                const std::uint64_t region=a.offset>>30,begin=(region<<30)+(4u<<20),end=((region+1)<<30)-(4u<<20);
                if((b.offset>>30)!=region||a.offset<begin||b.offset<begin||a.offset+a.bytes()>end||b.offset+b.bytes()>end)
                    throw std::invalid_argument("Vector pair violates qualified same-file range scheduling");
            }
        }
    }
public:
    VectoredSourceBatch(Reader reader,void *context):reader_(reader),context_(context) {
        if(!reader)throw std::invalid_argument("An exact vector reader is required");
    }
    VectoredSourceBatch(const VectoredSourceBatch &)=delete;
    VectoredSourceBatch &operator=(const VectoredSourceBatch &)=delete;
    void start() {
        std::unique_lock<std::mutex> lock(mutex_);
        if(ready_||failed_||worker_.joinable())throw std::logic_error("A fresh vector owner is required");
        producer_=std::this_thread::get_id();worker_=std::thread([this]{run();});
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return ready_;})) {
            failed_=uncertain_=true;throw std::runtime_error("Vector worker startup is uncertain; backing retained");
        }
    }
    void read(const VectoredRead *requests,unsigned count) {
        owner();validate(requests,count);
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(!ready_||stop_||failed_||uncertain_||pending_||!caller_done_||!worker_done_)
                throw std::logic_error("Vector owner is pending or quarantined");
            for(unsigned i=0;i<count;++i)requests_[i]=requests[i];
            caller_done_=false;worker_done_=count==1;pending_=count==2;
            if(pending_)changed_.notify_all();
        }
        std::int64_t result=-1;bool threw=false;
        try{result=reader_(context_,requests_[0]);}catch(...){threw=true;}
        std::unique_lock<std::mutex> lock(mutex_);caller_done_=true;
        if(threw)failed_=uncertain_=true;
        if(result!=static_cast<std::int64_t>(requests_[0].bytes()))failed_=true;
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return worker_done_;})) {
            failed_=uncertain_=true;throw std::runtime_error("Vector I/O completion is uncertain; backing retained");
        }
        if(failed_||uncertain_)throw std::runtime_error("Vector I/O did not return every expected byte");
    }
    bool completion_known() {
        std::lock_guard<std::mutex> lock(mutex_);
        return ready_&&!stop_&&!uncertain_&&!pending_&&caller_done_&&worker_done_&&worker_.joinable();
    }
    void stop_completed() {
        owner();
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(!ready_||stop_||uncertain_||pending_||!caller_done_||!worker_done_||!worker_.joinable())
                throw std::logic_error("Vector shutdown requires positive caller and worker completion");
            stop_=true;changed_.notify_all();
        }
        worker_.join();
    }
};
}
