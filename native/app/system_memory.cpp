// SPDX-License-Identifier: MIT
#include "system_memory.h"
#include "memory_backpressure.h"
#include "profile_clock.h"
#include <ps5platform/kernel.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <unistd.h>
namespace qwen_app {
namespace {
std::uint32_t scalar(const char * name) {
    std::uint32_t value=0;std::size_t bytes=sizeof(value);
    if(sysctlbyname(name,&value,&bytes,nullptr,0) || bytes!=sizeof(value))
        throw std::runtime_error("A required native memory counter is unavailable");
    return value;
}
}
SystemMemoryObservation observe_native_system_memory() {
    SystemMemoryObservation result;
    const auto first=scalar("vm.stats.vm0.v_free_count");
    result.page_size=scalar("hw.pagesize");
    result.kernel_pages=scalar("vm.stats.vm0.v_page_count");
    result.kernel_minimum=scalar("vm.stats.vm0.v_free_min");
    result.kernel_target=scalar("vm.stats.vm0.v_free_target");
    result.kernel_reserved=scalar("vm.stats.vm0.v_free_reserved");
    std::size_t flexible=0;
    if(sceKernelAvailableFlexibleMemorySize(&flexible)!=0)
        throw std::runtime_error("Fresh native Flexible availability is required");
    result.flexible_available=flexible;
    result.kernel_free=std::min(first,scalar("vm.stats.vm0.v_free_count"));
    return result;
}
namespace {
MemoryBackpressure admission_gate;
class NativeAdmissionOps final : public MemoryAdmissionOps {
public:
    SystemMemoryObservation observe() override {return observe_native_system_memory();}
    std::uint64_t now_ns() override {
        return std::chrono::duration_cast<std::chrono::nanoseconds>(ProfileClock::now().time_since_epoch()).count();
    }
    void pause_ns(std::uint64_t ns) override {
        if(!ns||ns>MemoryBackpressure::poll_interval_ns||usleep(useconds_t((ns+999)/1000))!=0)
            throw std::runtime_error("Bounded passive memory admission wait failed");
    }
};
}
void enable_native_memory_backpressure(){admission_gate.enable();}
SystemMemoryObservation admit_native_system_memory(){NativeAdmissionOps ops;return admission_gate.admit(ops);}
SystemMemoryObservation admit_native_startup_memory(){NativeAdmissionOps ops;return admission_gate.admit(ops,true);}
MemoryBackpressureStats native_memory_backpressure_stats(){return admission_gate.stats();}
}
