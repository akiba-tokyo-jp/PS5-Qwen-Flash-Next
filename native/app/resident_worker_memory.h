// SPDX-License-Identifier: MIT
// Same native process, allocator and actual ExpertPrefetchIO implementation.
// Measure lifecycle metadata only; do not repeat original I/O job validation.
#pragma once
#include <atomic>
namespace {
struct ResidentWorkerMemory {std::uint64_t worker_pages=0,idle_pages=0;unsigned completed=0;};
static ResidentWorkerMemory resident_worker_memory() {
    ResidentWorkerMemory result;
    for(unsigned i=0;i<4;++i) {
        (void)qwen_app::admit_native_system_memory();
        resident_sample("worker_matched_idle_before");const auto idle=resident_samples[resident_sample_count-1].memory.kernel_free;
        if(usleep(50000))throw std::runtime_error("Worker matched idle did not return");
        resident_sample("worker_matched_idle_after");const auto after_idle=resident_samples[resident_sample_count-1].memory.kernel_free;
        if(idle>after_idle)result.idle_pages=std::max(result.idle_pages,std::uint64_t(idle-after_idle));
        (void)qwen_app::admit_native_system_memory();
        resident_sample("worker_lifecycle_before");const auto before=resident_samples[resident_sample_count-1].memory.kernel_free;
        auto worker=std::make_unique<qwen_app::ExpertPrefetchIO>();
        try {
            resident_sample("worker_constructed");
            auto done=std::make_shared<std::atomic<unsigned>>(0);
            resident_worker_completion_unknown=true;
            worker->submit([done]{done->store(1,std::memory_order_release);});
            worker->complete();
            if(done->load(std::memory_order_acquire)!=1)throw std::runtime_error("Worker CPU marker did not complete");
            resident_sample("worker_CPU_job_completed");worker->close_completed();worker.reset();
            resident_worker_completion_unknown=false;
            resident_sample("worker_joined_and_closed");++result.completed;
        }catch(...) {worker.release();throw;}
        for(unsigned j=resident_sample_count-3;j<resident_sample_count;++j) {
            const auto current=resident_samples[j].memory.kernel_free;
            if(before>current)result.worker_pages=std::max(result.worker_pages,std::uint64_t(before-current));
        }
    }
    if(result.completed!=4)throw std::runtime_error("All four native worker lifetimes must close positively");
    return result;
}
}
