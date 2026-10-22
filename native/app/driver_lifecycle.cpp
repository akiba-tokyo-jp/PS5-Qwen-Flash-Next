// SPDX-License-Identifier: MIT
#include "driver_lifecycle.h"
#include <limits>
#include <stdexcept>

namespace qwen_app {
DriverLifecycle::DriverLifecycle(DriverOperations operations) : ops_(operations) {
    if (!ops_.open_log || !ops_.platform_init || !ops_.prepare || !ops_.owner_ready || !ops_.snapshot ||
        !ops_.kick_snapshot || !ops_.retire_quiet || !ops_.checkpoint || !ops_.retain ||
        !ops_.device_wait_idle || !ops_.stage)
        throw std::invalid_argument("Complete native driver operations are required");
}

void DriverLifecycle::retain_fault() noexcept {
    const auto previous = state_.exchange(State::faulted);
    if (previous != State::cold && previous != State::faulted) ops_.retain();
    // Keep the producer lease and every resource alive after uncertainty.
}

[[noreturn]] void DriverLifecycle::reject(const char * reason) {
    retain_fault();
    ops_.stage(reason);
    throw std::runtime_error(reason);
}

void DriverLifecycle::initialize(const char * journal) {
    State expected = State::cold;
    if (!state_.compare_exchange_strong(expected, State::initializing))
        reject("Native driver initialization may be attempted only once");
    try {
        ops_.stage("native_driver_before_own_journal AGC_not_started=1");
        if (!journal || ops_.open_log(journal)) reject("Native driver own journal was not admitted");
        ops_.stage("native_driver_before_platform_init explicit_AGC_owner=1");
        if (!ops_.platform_init() || agc_requests_.load() != 1 || agc_result_.load() != 0 || faulted())
            reject("Native driver sole AGC initialization was not admitted");
        ops_.stage("native_driver_platform_initialized_before_owner_prepare");
        if (ops_.prepare()) reject("Native per-BO metadata preparation failed");
        ps5_ai_arena_stats owner{};
        ops_.snapshot(&owner);
        if (!ops_.owner_ready() || owner.reserved_bytes || owner.used_bytes || owner.live_allocations ||
            owner.physical_owned || owner.mapping_owned || owner.mapping_uncertain ||
            owner.gpu_fault_retained || owner.global_capacity_measured)
            reject("Native driver must have an empty exact owner before Vulkan discovery");
        if (!ops_.checkpoint()) reject("Native prepared-owner journal did not complete");
        state_.store(State::ready);
        ops_.stage("native_driver_owner_ready owned_BO_bytes=0 constructor_allocations=unknown");
    } catch (...) { retain_fault(); throw; }
}

std::int32_t DriverLifecycle::initialize_agc(std::uint32_t version,
                                           std::int32_t (*operation)(std::uint32_t)) {
    // This wrapper is called by RADV's call_once, never by the frontend itself.
    if (state_.load() != State::initializing || version != 8 || !operation || agc_requests_.fetch_add(1) != 0) {
        retain_fault();
        return -1;
    }
    ops_.stage("native_driver_before_explicit_AGC8 hard_timeout=not_established");
    const auto result = operation(version);
    agc_result_.store(result);
    ops_.stage(result == 0 ? "native_driver_explicit_AGC8_completed" : "native_driver_explicit_AGC8_failed");
    if (result) retain_fault();
    return result;
}

void DriverLifecycle::begin_work() {
    if (!ready()) reject("Native driver is not available for a producer");
    bool expected = false;
    if (!producer_active_.compare_exchange_strong(expected, true))
        reject("Overlapping native frontend producers are forbidden");
    producer_ = std::this_thread::get_id();
    ops_.stage("native_driver_single_producer_entered");
}

void DriverLifecycle::register_device(std::uintptr_t device) {
    if (!ready() || !producer_active_.load() || !device)
        reject("Native device creation requires an admitted producer");
    std::uintptr_t expected = 0;
    if (!device_.compare_exchange_strong(expected, device))
        reject("Only one native Vulkan device may be registered");
}

void DriverLifecycle::before_submit() {
    if (!ready() || !producer_active_.load() || !device_.load())
        reject("Native queue submission has no admitted frontend producer");
    if(!queue_calls_.try_lock())reject("Concurrent native queue host access is forbidden");
    if(!ready() || !producer_active_.load()) {queue_calls_.unlock();reject("Native producer ended before queue submission");}
    const auto count = submits_.fetch_add(1);
    if (count == std::numeric_limits<std::uint64_t>::max()) {
        queue_calls_.unlock();
        reject("Native submission counter exhausted; resources retained");
    }
}
void DriverLifecycle::after_submit() { queue_calls_.unlock(); }

void DriverLifecycle::complete_work() { finish_boundary(true); }
void DriverLifecycle::checkpoint_work() { finish_boundary(false); }
void DriverLifecycle::finish_boundary(bool end_producer) {
    if (!ready() || !producer_active_.load() || producer_ != std::this_thread::get_id())
        reject("Only the active frontend producer may complete native work");
    try {
        // Vulkan requires external host synchronization of all queues during
        // DeviceWaitIdle. Refuse overlap instead of waiting on an unknown call.
        std::unique_lock<std::mutex> queues(queue_calls_,std::try_to_lock);
        if(!queues.owns_lock())reject("Native queue call still active at the frontend boundary");
        const auto submitted = submits_.load();
        const auto device = device_.load();
        if (device) {
            ops_.stage("native_driver_before_positive_device_idle");
            if (ops_.device_wait_idle(device)) reject("Native device idle did not positively complete");
            ops_.stage("native_driver_device_idle_completed");
        }
        if (submitted != submits_.load()) reject("Native submissions advanced during a quiet boundary");
        ps5_ai_arena_kick_stats kick{};
        if (ops_.kick_snapshot(&kick) || kick.pending || kick.active || kick.submit_inflight ||
            kick.fault_retained || !kick.log_healthy || !ops_.owner_ready())
            reject("Native completion worker is not positively quiet");
        if (submitted) {
            if (!device || !kick.initialized || !kick.thread_started || !kick.requested_epoch ||
                kick.requested_epoch != kick.completed_epoch)
                reject("Native submission completion epoch is not admitted");
            ops_.stage("native_driver_before_completed_epoch_retirement");
            if (ops_.retire_quiet(kick.completed_epoch) != 1)
                reject("Native retired ownership could not be confirmed");
        } else if (kick.requested_epoch || kick.completed_epoch) {
            reject("Native worker observed untracked submissions");
        }
        ps5_ai_arena_stats owner{};
        ops_.snapshot(&owner);
        if (owner.mapping_uncertain || owner.gpu_fault_retained || owner.global_capacity_measured ||
            submitted != submits_.load() || !ops_.checkpoint())
            reject("Native completed-owner accounting or journal is uncertain");
        ops_.stage(end_producer ? "native_driver_producer_completed_resources_owned" : "native_driver_checkpoint_completed_producer_retained");
        if(end_producer)producer_active_.store(false);
    } catch (...) { retain_fault(); throw; }
}
}
