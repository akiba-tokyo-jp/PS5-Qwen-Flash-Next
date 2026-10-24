// SPDX-License-Identifier: MIT
#pragma once
#include "../driver/arena.h"
#include <atomic>
#include <cstdint>
#include <thread>
#include <mutex>

namespace qwen_app {
struct DriverOperations {
    int (*open_log)(const char *);
    bool (*platform_init)();
    int (*prepare)();
    int (*owner_ready)();
    void (*snapshot)(ps5_ai_arena_stats *);
    int (*kick_snapshot)(ps5_ai_arena_kick_stats *);
    int (*retire_quiet)(std::uint64_t);
    bool (*checkpoint)();
    void (*retain)();
    int (*device_wait_idle)(std::uintptr_t);
    void (*stage)(const char *);
};

// One frontend producer may schedule internal backend threads. Only its own
// completed synchronous boundary may retire nodes; queue counts are not proof.
class DriverLifecycle {
public:
    explicit DriverLifecycle(DriverOperations operations);
    void initialize(const char * journal);
    std::int32_t initialize_agc(std::uint32_t version, std::int32_t (*operation)(std::uint32_t));
    void begin_work();
    void register_device(std::uintptr_t device);
    void before_submit();
    void after_submit();
    void complete_work();
    void checkpoint_work();
    void retain_fault() noexcept;
    bool ready() const { return state_.load() == State::ready; }
    bool faulted() const { return state_.load() == State::faulted; }
private:
    enum class State { cold, initializing, ready, faulted };
    [[noreturn]] void reject(const char *);
    void finish_boundary(bool end_producer);
    DriverOperations ops_;
    std::atomic<State> state_{State::cold};
    std::atomic<bool> producer_active_{false};
    std::thread::id producer_;
    std::atomic<std::uintptr_t> device_{0};
    std::atomic<std::uint64_t> submits_{0};
    std::atomic<unsigned> agc_requests_{0};
    std::atomic<std::int32_t> agc_result_{-1};
    std::mutex queue_calls_;
};
}
