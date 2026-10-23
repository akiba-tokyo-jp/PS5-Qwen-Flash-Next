// SPDX-License-Identifier: MIT
#include "system_memory.h"
#include <ps5platform/kernel.h>
#include <sys/types.h>
#include <sys/sysctl.h>
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
}
