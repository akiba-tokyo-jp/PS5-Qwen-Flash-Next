// SPDX-License-Identifier: MIT
#pragma once
#include "ready_expert_wave.h"
#include <chrono>
#include <condition_variable>
#include <exception>
namespace qwen_app {
enum class ReadySourceMode { serial,overlap };
struct ReadySourceSnapshot {
    bool first_returned=false,second_released=false,second_returned=false;
    bool thread_returned=false,joined=false,failed=false;
};
// One source coordinator runs outside the sole GPU producer. Its callback may
// use the existing two-call VectoredSourceBatch; this preserves I/O depth two
// while the original producer submits a graph. No callback runs on the GPU
// producer and no second group is released before its real wave-zero lease.
//
// A callback must return with all started native I/O positively completed. An
// idle retained inner worker may persist across the groups, but must be joined
// before the final callback returns. The callback owns durable I/O plans,
// exact source/hash checks and ReadyExpertWave role completions. This owner
// grants no pointer, memory or native completion proof.
// Construct it inside the real nested backing callback. On uncertain completion
// retain this object and its entire callback graph until ordinary OS teardown.
class ReadySourceCoordinator {
public:
    using Fill=void (*)(ReadyExpertWave &,unsigned group,void *);
    using Deadline=std::chrono::steady_clock::time_point;
private:
    const std::thread::id producer_=std::this_thread::get_id();
    std::thread worker_;std::mutex mutex_;std::condition_variable changed_;
    ReadyExpertWave *wave_=nullptr;Fill fill_=nullptr;void *opaque_=nullptr;
    ReadySourceMode mode_=ReadySourceMode::serial;
    ReadySourceSnapshot state_{};std::exception_ptr error_;
    bool attempted_=false,admitted_=false,cancel_=false;
    void producer()const {
        if(std::this_thread::get_id()!=producer_)throw std::logic_error("Ready source coordinator requires its original GPU producer");
    }
    void run()noexcept {
        try {
            {std::unique_lock<std::mutex> lock(mutex_);changed_.wait(lock,[&]{return admitted_||cancel_;});if(cancel_)throw std::runtime_error("Ready source binding did not complete");}
            fill_(*wave_,0,opaque_);
            {
                std::unique_lock<std::mutex> lock(mutex_);state_.first_returned=true;changed_.notify_all();
                if(mode_==ReadySourceMode::overlap)changed_.wait(lock,[&]{return state_.second_released||cancel_;});
                if(cancel_)throw std::runtime_error("Ready source second group cancelled before I/O");
            }
            fill_(*wave_,1,opaque_);
            {std::lock_guard<std::mutex> lock(mutex_);state_.second_returned=true;}
        }catch(...) {
            std::lock_guard<std::mutex> lock(mutex_);error_=std::current_exception();state_.failed=true;
        }
        std::lock_guard<std::mutex> lock(mutex_);state_.thread_returned=true;changed_.notify_all();
    }
    void wait(std::unique_lock<std::mutex> &lock,Deadline deadline,bool first) {
        const auto ready=[&]{return (first?state_.first_returned:state_.thread_returned)||state_.failed;};
        if(!changed_.wait_until(lock,deadline,ready)){state_.failed=true;throw std::runtime_error("Ready source completion deadline exceeded; all owners retained");}
        if(state_.failed){if(error_)std::rethrow_exception(error_);throw std::runtime_error("Ready source owner is quarantined");}
    }
public:
    ReadySourceCoordinator()=default;
    ReadySourceCoordinator(const ReadySourceCoordinator&)=delete;
    ReadySourceCoordinator&operator=(const ReadySourceCoordinator&)=delete;
    void start(ReadyExpertWave &wave,ReadySourceMode mode,Fill fill,void *opaque) {
        producer();std::unique_lock<std::mutex> lock(mutex_);
        if(attempted_||!fill||(mode!=ReadySourceMode::serial&&mode!=ReadySourceMode::overlap)||!wave.may_overlap_groups())
            throw std::invalid_argument("A fresh callback and two distinct actual ready groups are required");
        attempted_=true;wave_=&wave;fill_=fill;opaque_=opaque;mode_=mode;
        // The reader cannot start until binding succeeded on the original GPU
        // producer. Binding failure returns its parked thread before throwing.
        worker_=std::thread([this]{run();});
        try{wave.bind_reader(worker_.get_id());}catch(...) {
            cancel_=true;state_.failed=true;changed_.notify_all();lock.unlock();worker_.join();
            lock.lock();state_.joined=true;throw;
        }
        admitted_=true;changed_.notify_all();
    }
    void wait_first_returned(Deadline deadline) {
        producer();std::unique_lock<std::mutex> lock(mutex_);
        if(!admitted_||state_.joined)throw std::logic_error("Ready source group zero has no active owner");
        wait(lock,deadline,true);
    }
    std::array<bool,10> begin_first_wave_and_release_second(std::uint64_t epoch) {
        producer();std::lock_guard<std::mutex> lock(mutex_);
        if(!admitted_||mode_!=ReadySourceMode::overlap||!state_.first_returned||state_.second_released||state_.failed||state_.joined)
            throw std::logic_error("The second source group requires one returned first group and one release");
        // Acquire group zero's real wave lease here, before making group one
        // runnable. An externally started wrong wave cannot release source I/O.
        const auto selected=wave_->begin_wave(0,epoch);
        state_.second_released=true;changed_.notify_all();return selected;
    }
    void join_completed(Deadline deadline) {
        producer();std::unique_lock<std::mutex> lock(mutex_);
        if(!admitted_||!worker_.joinable()||state_.joined)throw std::logic_error("Ready source thread has no single pending join");
        wait(lock,deadline,false);
        if(!state_.first_returned||!state_.second_returned)throw std::logic_error("Both source group callbacks must have returned");
        lock.unlock();worker_.join();lock.lock();state_.joined=true;
    }
    // For a known callback exception or producer refusal, stop only a parked
    // future group. This is not native-I/O cancellation and never authorizes
    // backing retirement. A running callback must still return by itself.
    void retain_and_join_returned_thread(Deadline deadline) {
        producer();std::unique_lock<std::mutex> lock(mutex_);
        if(!attempted_||!worker_.joinable()||state_.joined)throw std::logic_error("No retained coordinator thread can be joined");
        state_.failed=true;cancel_=true;changed_.notify_all();
        if(!changed_.wait_until(lock,deadline,[&]{return state_.thread_returned;}))
            throw std::runtime_error("Retained coordinator thread is still running; owners retained");
        lock.unlock();worker_.join();lock.lock();state_.joined=true;
    }
    ReadySourceSnapshot snapshot(){std::lock_guard<std::mutex> lock(mutex_);return state_;}
};
}
