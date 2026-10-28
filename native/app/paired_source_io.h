// SPDX-License-Identifier: MIT
#pragma once
#include "mapped_source.h"
#include <condition_variable>
#include <exception>
#include <mutex>

namespace qwen_app {
// One persistent CPU I/O worker, with the other read on the existing producer.
// The owner retains this object and its buffers after any uncertain completion.
// No GPU command, descriptor mutation, memory admission or retry runs here.
class PairedSourceIO {
    SourceReadOps & ops_;
    std::mutex mutex_;
    std::condition_variable changed_;
    std::thread worker_;
    SourceReadRequest request_{};
    std::int64_t result_ = -1;
    std::exception_ptr error_;
    ProfileClock::time_point queued_at_{};
    std::uint64_t worker_read_ns_ = 0, worker_dispatch_ns_ = 0;
    bool ready_ = false, pending_ = false, completed_ = true, stop_ = false, failed_ = false, uncertain_ = false;
    std::array<SourceReadRequest,6> batch_requests_{};
    std::array<std::int64_t,6> batch_results_{};
    std::array<std::exception_ptr,6> batch_errors_{};
    unsigned batch_next_=0,batch_returned_=0;
    bool batch_mode_=false;

    void batch_lane() noexcept {
        for(;;) {
            std::unique_lock<std::mutex> lock(mutex_);
            if(batch_next_==6||failed_)return;
            const auto index=batch_next_++;const auto request=batch_requests_[index];lock.unlock();
            std::int64_t result=-1;std::exception_ptr error;
            try{result=ops_.read_at(request.fd,request.target,request.bytes,request.offset);}
            catch(...){error=std::current_exception();}
            lock.lock();batch_results_[index]=result;batch_errors_[index]=error;++batch_returned_;
            if(error)uncertain_=true;
            if(error||result!=std::int64_t(request.bytes))failed_=true;
        }
    }

    void run() noexcept {
        std::unique_lock<std::mutex> lock(mutex_);
        ready_ = true; changed_.notify_all();
        for (;;) {
            changed_.wait(lock, [&] { return pending_ || stop_; });
            if (stop_) return;
            if(batch_mode_) {
                lock.unlock();batch_lane();lock.lock();
                completed_=true;pending_=false;changed_.notify_all();continue;
            }
            const auto request = request_;
            const auto queued_at = queued_at_;
            lock.unlock();
            const auto read_started = ProfileClock::now();
            std::int64_t result = -1;
            std::exception_ptr error;
            try { result = ops_.read_at(request.fd, request.target, request.bytes, request.offset); }
            catch (...) { error = std::current_exception(); }
            const auto read_ns = profile_elapsed_ns(read_started);
            lock.lock();
            worker_read_ns_ = read_ns;
            worker_dispatch_ns_ = std::chrono::duration_cast<std::chrono::nanoseconds>(read_started - queued_at).count();
            result_ = result; error_ = error; completed_ = true; pending_ = false;
            changed_.notify_all();
        }
    }
public:
    explicit PairedSourceIO(SourceReadOps & ops) : ops_(ops) {}
    PairedSourceIO(const PairedSourceIO &) = delete;
    PairedSourceIO & operator=(const PairedSourceIO &) = delete;
    // The native owner must call stop_completed() before destruction. A failed
    // start/read leaves the owned object alive for ordinary process shutdown.
    ~PairedSourceIO() = default;

    void start() {
        std::unique_lock<std::mutex> lock(mutex_);
        if (worker_.joinable() || ready_ || failed_) throw std::logic_error("A fresh paired I/O worker is required");
        worker_ = std::thread([this] { run(); });
        if (!changed_.wait_for(lock, std::chrono::seconds(10), [&] { return ready_; })) {
            failed_ = uncertain_ = true;
            throw std::runtime_error("Paired I/O worker startup is uncertain; owner retained");
        }
    }
    std::array<std::int64_t, 2> read(const std::array<SourceReadRequest, 2> & requests) {
        for (const auto & request : requests) {
            const auto at = reinterpret_cast<std::uintptr_t>(request.target);
            if (request.fd < 0 || !at || !request.bytes || request.bytes > model_read_window / 2 ||
                at % model_read_alignment || request.bytes % model_read_alignment ||
                request.offset % model_read_alignment || request.bytes > UINTPTR_MAX - at)
                throw std::invalid_argument("Paired I/O requires bounded aligned owned requests");
        }
        const auto first = reinterpret_cast<std::uintptr_t>(requests[0].target);
        const auto second = reinterpret_cast<std::uintptr_t>(requests[1].target);
        if (first < second + requests[1].bytes && second < first + requests[0].bytes)
            throw std::invalid_argument("Paired I/O destinations must be disjoint");
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (!ready_ || stop_ || failed_ || pending_ || !completed_)
                throw std::runtime_error("Paired I/O worker is busy or quarantined");
            request_ = requests[1]; result_ = -1; error_ = nullptr; queued_at_ = ProfileClock::now();
            completed_ = false; pending_ = true; changed_.notify_all();
        }
        std::array<std::int64_t, 2> results{-1, -1};
        std::exception_ptr producer_error;
        try { results[0] = ops_.read_at(requests[0].fd, requests[0].target, requests[0].bytes, requests[0].offset); }
        catch (...) { producer_error = std::current_exception(); }
        std::unique_lock<std::mutex> lock(mutex_);
        // A timeout cannot cancel an opaque read. Keep its request and backing
        // intact, refuse new jobs and let the application retain its graph.
        if (!changed_.wait_for(lock, std::chrono::seconds(10), [&] { return completed_; })) {
            failed_ = uncertain_ = true;
            throw std::runtime_error("Paired source completion is uncertain; buffers retained");
        }
        results[1] = result_;
        if (producer_error || error_ || results[0] < 0 || results[1] < 0) {
            failed_ = true;
            if (producer_error) std::rethrow_exception(producer_error);
            if (error_) std::rethrow_exception(error_);
        }
        return results;
    }
    // The same persistent worker and producer take six known destinations.
    // Preserve the existing pair/pipeline paths when this explicit API is idle.
    std::array<std::int64_t,6> read_batch(const std::array<SourceReadRequest,6> &requests) {
        for(unsigned i=0;i<6;++i) {
            const auto &r=requests[i];const auto at=reinterpret_cast<std::uintptr_t>(r.target);
            if(r.fd<0||!at||!r.bytes||r.bytes>model_read_window/2||at%model_read_alignment||
               r.bytes%model_read_alignment||r.offset%model_read_alignment||r.bytes>UINTPTR_MAX-at||
               r.offset>std::uint64_t(INT64_MAX)-r.bytes)
                throw std::invalid_argument("Six-demand reads require bounded aligned owned destinations");
            for(unsigned j=0;j<i;++j){const auto other=reinterpret_cast<std::uintptr_t>(requests[j].target);
                if(at<other+requests[j].bytes&&other<at+r.bytes)
                    throw std::invalid_argument("Six-demand destination leases overlap");}
        }
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if(!ready_||stop_||failed_||pending_||!completed_||batch_mode_)
                throw std::runtime_error("The retained source worker cannot enter six-demand delivery");
            batch_requests_=requests;batch_results_.fill(-1);batch_errors_.fill(nullptr);
            batch_next_=batch_returned_=0;batch_mode_=pending_=true;completed_=false;changed_.notify_all();
        }
        batch_lane();std::unique_lock<std::mutex> lock(mutex_);
        if(!changed_.wait_for(lock,std::chrono::seconds(10),[&]{return completed_;})) {
            failed_=uncertain_=true;throw std::runtime_error("Six-demand completion is uncertain; all backing retained");
        }
        if(failed_||batch_returned_!=6) {
            for(const auto &error:batch_errors_)if(error)std::rethrow_exception(error);
            throw std::runtime_error("The complete six-demand batch did not return exact bytes");
        }
        batch_mode_=false;return batch_results_;
    }
    // Exactly one read can be in flight. The second read overlaps only the
    // first synchronous consumer, which always runs on the original producer.
    SourcePipelineTimes pipeline(const std::array<SourceReadRequest, 2> & requests,
            const std::array<std::uint64_t, 2> & expected,
            const std::function<void(unsigned)> & before_read,
            const std::function<void(unsigned, const void *)> & consume) {
        for (unsigned i = 0; i < 2; ++i) {
            const auto & r = requests[i]; const auto at = reinterpret_cast<std::uintptr_t>(r.target);
            if (r.fd < 0 || !at || !r.bytes || r.bytes > model_read_window / 2 ||
                at % model_read_alignment || r.bytes % model_read_alignment || r.offset % model_read_alignment ||
                r.bytes > UINTPTR_MAX - at || !expected[i] || expected[i] > r.bytes)
                throw std::invalid_argument("A pipeline requires exact bounded aligned read requests");
        }
        const auto a = reinterpret_cast<std::uintptr_t>(requests[0].target), b = reinterpret_cast<std::uintptr_t>(requests[1].target);
        if (a < b + requests[1].bytes && b < a + requests[0].bytes)
            throw std::invalid_argument("Pipeline read windows must be disjoint");
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (!ready_ || stop_ || failed_ || pending_ || !completed_)
                throw std::runtime_error("The source pipeline is busy or quarantined");
        }
        SourcePipelineTimes timing;
        try {
            before_read(0);
            const auto started = ProfileClock::now();
            const auto got = ops_.read_at(requests[0].fd, requests[0].target, requests[0].bytes, requests[0].offset);
            timing.producer_wait_ns = profile_elapsed_ns(started);
            if (got < 0 || std::uint64_t(got) != expected[0])
                throw std::runtime_error("The first pipelined source read did not complete exactly");
            before_read(1);
        } catch (...) { std::lock_guard<std::mutex> lock(mutex_); failed_ = true; throw; }
        {
            std::lock_guard<std::mutex> lock(mutex_);
            request_ = requests[1]; result_ = -1; error_ = nullptr; queued_at_ = ProfileClock::now();
            completed_ = false; pending_ = true; changed_.notify_all();
        }
        std::exception_ptr consumer_error;
        try { consume(0, requests[0].target); } catch (...) { consumer_error = std::current_exception(); }
        const auto wait_started = ProfileClock::now();
        std::unique_lock<std::mutex> lock(mutex_);
        if (!changed_.wait_for(lock, std::chrono::seconds(10), [&] { return completed_; })) {
            failed_ = uncertain_ = true;
            throw std::runtime_error("Pipelined source completion is uncertain; backing retained");
        }
        timing.producer_wait_ns += profile_elapsed_ns(wait_started);
        timing.worker_read_ns = worker_read_ns_; timing.worker_dispatch_ns = worker_dispatch_ns_;
        if (consumer_error || error_ || result_ < 0 || std::uint64_t(result_) != expected[1]) {
            failed_ = true;
            if (consumer_error) std::rethrow_exception(consumer_error);
            if (error_) std::rethrow_exception(error_);
            throw std::runtime_error("The second pipelined source read did not complete exactly");
        }
        lock.unlock();
        try { consume(1, requests[1].target); }
        catch (...) { std::lock_guard<std::mutex> lock(mutex_); failed_ = true; throw; }
        return timing;
    }
    void require_completed() {
        std::lock_guard<std::mutex> lock(mutex_);
        if(!ready_||stop_||failed_||uncertain_||pending_||!completed_||!worker_.joinable())
            throw std::runtime_error("An exclusive metadata lease requires a healthy idle source worker");
    }
    void stop_completed() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            if (!ready_ || uncertain_ || pending_ || !completed_ || !worker_.joinable())
                throw std::runtime_error("Paired I/O shutdown requires healthy known completion");
            stop_ = true; changed_.notify_all();
        }
        worker_.join();
    }
};
}
