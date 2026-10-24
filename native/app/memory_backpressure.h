// SPDX-License-Identifier: MIT
#pragma once
#include "system_memory.h"
#include <limits>
namespace qwen_app {
struct MemoryAdmissionOps {
    virtual ~MemoryAdmissionOps()=default;
    virtual SystemMemoryObservation observe()=0;
    virtual std::uint64_t now_ns()=0;
    virtual void pause_ns(std::uint64_t)=0;
};
// Call only before new I/O or at a positively completed producer boundary.
// Waiting observes independent OS paging; it issues no I/O/GPU operation,
// reclamation, allocation or retry. Every admitted result passes the original
// minimum/reserve predicate. The total delay budget spans the whole process.
class MemoryBackpressure {
    MemoryBackpressureStats stats_;
    std::uint64_t boundary_ns_,total_ns_,poll_ns_;
    bool failed_=false;
public:
    static constexpr std::uint64_t boundary_limit_ns=20000000000ull;
    static constexpr std::uint64_t total_limit_ns=60000000000ull;
    static constexpr std::uint64_t poll_interval_ns=100000000ull;
    explicit MemoryBackpressure(std::uint64_t boundary=boundary_limit_ns,
            std::uint64_t total=total_limit_ns,std::uint64_t poll=poll_interval_ns)
        :boundary_ns_(boundary),total_ns_(total),poll_ns_(poll) {
        if(!boundary||!total||!poll||poll>boundary||boundary>total)
            throw std::invalid_argument("Invalid bounded memory admission wait policy");
    }
    void enable() {
        if(stats_.enabled||failed_)throw std::logic_error("Memory backpressure may only be enabled once");
        stats_.enabled=true;
    }
    const MemoryBackpressureStats & stats() const {return stats_;}
private:
    SystemMemoryObservation admit_impl(MemoryAdmissionOps & ops, bool require_kernel_target) {
        bool waiting=false;std::uint64_t boundary_wait=0;
        for(;;) {
            stats_.last_qualified=false;stats_.last=ops.observe();++stats_.observations;
            try {
                (void)qualified_system_headroom(stats_.last);
                if (require_kernel_target && stats_.last.kernel_free < stats_.last.kernel_target)
                    throw KernelMemoryPressure();
                stats_.last_qualified=true;
                if(waiting)++stats_.recovered_admissions;
                return stats_.last;
            } catch(const KernelMemoryPressure &) {
                if(!stats_.enabled)throw;
            }
            if(!waiting){waiting=true;++stats_.pressure_events;}
            if(boundary_wait>=boundary_ns_||stats_.wait_ns>=total_ns_)throw KernelMemoryPressure();
            const auto delay=std::min({poll_ns_,boundary_ns_-boundary_wait,total_ns_-stats_.wait_ns});
            const auto before=ops.now_ns();ops.pause_ns(delay);const auto after=ops.now_ns();
            if(after<=before||after-before>std::numeric_limits<std::uint64_t>::max()-stats_.wait_ns)
                throw std::runtime_error("Memory admission wait clock did not advance safely");
            const auto elapsed=after-before;
            stats_.wait_ns+=elapsed;++stats_.pause_calls;
            if(elapsed>std::numeric_limits<std::uint64_t>::max()-boundary_wait)
                throw std::runtime_error("Memory admission wait interval overflow");
            boundary_wait+=elapsed;
            if(boundary_wait>boundary_ns_||stats_.wait_ns>total_ns_)throw KernelMemoryPressure();
        }
    }
public:
    SystemMemoryObservation admit(MemoryAdmissionOps & ops, bool require_kernel_target = false) {
        if(failed_)throw std::runtime_error("A failed memory admission is quarantined; no retry");
        try {return admit_impl(ops, require_kernel_target);}
        catch(...) {if(stats_.enabled)failed_=true;throw;}
    }
};
}
