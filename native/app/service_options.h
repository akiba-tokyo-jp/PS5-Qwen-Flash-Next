// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <atomic>
namespace qwen_service {
inline std::atomic<unsigned> mode{0};
inline std::atomic<std::uint64_t> stage_pairs{0},stage_writes{0},stage_syncs{0};
inline char pending_stage[96]{};
inline std::atomic_flag pending_lock=ATOMIC_FLAG_INIT;
struct StageLock{StageLock(){while(pending_lock.test_and_set(std::memory_order_acquire)){}}~StageLock(){pending_lock.clear(std::memory_order_release);}};
inline bool has_pending(){StageLock lock;return pending_stage[0];}
inline bool ledger(){return mode.load(std::memory_order_relaxed)&1;}
inline bool pair_stages(){return mode.load(std::memory_order_relaxed)&2;}
}
