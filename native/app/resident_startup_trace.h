// SPDX-License-Identifier: MIT
// Included after the original native main helpers in the dedicated test entry.
#pragma once
namespace {
struct ResidentStartupSample {
    const char *phase;
    std::uint64_t ns;
    qwen_app::SystemMemoryObservation memory;
    std::uint64_t heap;
};
static std::array<ResidentStartupSample,64> resident_samples{};
static unsigned resident_sample_count;
static bool resident_worker_completion_unknown;
static void resident_sample(const char *phase) {
    if(resident_sample_count==resident_samples.size())throw std::runtime_error("Finite startup trace exhausted");
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
    resident_samples[resident_sample_count++]={phase,static_cast<std::uint64_t>(ns),qwen_app::observe_native_system_memory(),heap.mapped_bytes};
}
static Json resident_startup_report() {
    Json rows=Json::array();
    for(unsigned i=0;i<resident_sample_count;++i){const auto &s=resident_samples[i];
        rows.push_back({{"phase",s.phase},{"ns",s.ns},{"kernel_free_pages",s.memory.kernel_free},
            {"Flexible_available_bytes",s.memory.flexible_available},{"CPU_Direct_heap_bytes",s.heap},
            {"kernel_minimum_pages",s.memory.kernel_minimum},{"kernel_reserved_pages",s.memory.kernel_reserved}});}
    return {{"schema","ps5-qwen-resident-startup-memory-v1"},{"samples",rows},{"global_snapshots_not_exclusive_attribution",true}};
}
}
