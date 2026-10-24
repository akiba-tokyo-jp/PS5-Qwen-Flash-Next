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
    bool ready_ = false, pending_ = false, completed_ = true, stop_ = false, failed_ = false, uncertain_ = false;

    void run() noexcept {
        std::unique_lock<std::mutex> lock(mutex_);
        ready_ = true; changed_.notify_all();
        for (;;) {
            changed_.wait(lock, [&] { return pending_ || stop_; });
            if (stop_) return;
            const auto request = request_;
            lock.unlock();
            std::int64_t result = -1;
            std::exception_ptr error;
            try { result = ops_.read_at(request.fd, request.target, request.bytes, request.offset); }
            catch (...) { error = std::current_exception(); }
            lock.lock();
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
            request_ = requests[1]; result_ = -1; error_ = nullptr;
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
