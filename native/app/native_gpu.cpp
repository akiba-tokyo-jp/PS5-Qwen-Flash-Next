// SPDX-License-Identifier: MIT
#include "native_gpu.h"
#include "driver_lifecycle.h"
#include <stdexcept>
#include <string>
#ifndef QWEN_NATIVE_PLATFORM
#define QWEN_NATIVE_PLATFORM 0
#endif
extern "C" void qwen_native_stage(const char *);
extern "C" [[noreturn]] void qwen_native_halt(const char *);
#if QWEN_NATIVE_PLATFORM
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include "../driver/journal_metrics.h"
extern "C" {
bool radv_ps5_platform_init();
std::uint64_t radv_ps5_memory_pool_bytes();
std::uint64_t radv_ps5_memory_available_bytes();
PFN_vkVoidFunction vk_common_GetDeviceProcAddr(VkDevice,const char *);
std::int32_t __real_sceAgcInit(std::uint32_t);
bool ps5_ai_native_journal_debug_enabled() { return false; }
bool ps5_ai_native_journal_configure_debug(bool enabled) { return !enabled; }
}
namespace {
int wait_idle(std::uintptr_t value) {
    const auto device=reinterpret_cast<VkDevice>(value);
    const auto operation=reinterpret_cast<PFN_vkDeviceWaitIdle>(vk_common_GetDeviceProcAddr(device,"vkDeviceWaitIdle"));
    return operation ? operation(device) : VK_ERROR_INITIALIZATION_FAILED;
}
qwen_app::DriverLifecycle driver({qwen_ps5_driver_open_log,radv_ps5_platform_init,
    ps5_ai_arena_prepare,ps5_ai_driver_owner_ready,ps5_ai_arena_snapshot,
    ps5_ai_arena_kick_snapshot,ps5_ai_driver_retire_quiet,
    ps5_ai_native_arena_journal_checkpoint,ps5_ai_arena_retain_gpu_fault,wait_idle,qwen_native_stage});
template<class Operation> void checked(Operation operation) {
    try { operation(); }
    catch (...) { driver.retain_fault();qwen_native_halt("native_driver_frontend_contract_failed"); }
}
}
bool qwen_native_gpu_frontend_linked() { return true; }
qwen_app::NativeAllocatorBudget qwen_native_allocator_budget(std::uint64_t reported_device_total) {
    if(!ps5_ai_driver_owner_ready())throw std::runtime_error("Native allocator owner or journal is not ready");
    ps5_ai_arena_stats before{},after{};ps5_ai_arena_snapshot(&before);
    const auto pool_first=radv_ps5_memory_pool_bytes(),free_first=radv_ps5_memory_available_bytes();
    const auto free_last=radv_ps5_memory_available_bytes(),pool_last=radv_ps5_memory_pool_bytes();
    ps5_ai_arena_snapshot(&after);
    if(!ps5_ai_driver_owner_ready())throw std::runtime_error("Native allocator owner or journal changed during observation");
    const auto stage="native_Direct_budget_observation reported_total="+std::to_string(reported_device_total)+
        " pool_first="+std::to_string(pool_first)+" pool_last="+std::to_string(pool_last)+
        " free_first="+std::to_string(free_first)+" free_last="+std::to_string(free_last)+
        " owned_before="+std::to_string(before.used_bytes)+" owned_after="+std::to_string(after.used_bytes)+
        " fault_before="+std::to_string(before.gpu_fault_retained)+" uncertain_before="+std::to_string(before.mapping_uncertain);
    qwen_native_stage(stage.c_str());
    return qwen_app::qualify_native_allocator_budget(reported_device_total,pool_first,pool_last,free_first,free_last,before,after);
}
void qwen_native_gpu_initialize(const char * journal) { driver.initialize(journal); }
extern "C" std::int32_t __wrap_sceAgcInit(std::uint32_t version) {
    std::int32_t result=-1;checked([&]{result=driver.initialize_agc(version,__real_sceAgcInit);});return result;
}
extern "C" void qwen_native_driver_begin() { checked([]{driver.begin_work();}); }
extern "C" void qwen_native_driver_complete() { checked([]{driver.complete_work();}); }
extern "C" void qwen_native_driver_checkpoint() { checked([]{driver.checkpoint_work();}); }
extern "C" void qwen_native_driver_retain() { driver.retain_fault(); }
extern "C" void qwen_native_driver_before_submit() { checked([]{driver.before_submit();}); }
extern "C" void qwen_native_driver_after_submit() { driver.after_submit(); }
extern "C" void qwen_native_driver_register_device(std::uintptr_t device) { checked([&]{driver.register_device(device);}); }
#else
bool qwen_native_gpu_frontend_linked() { return false; }
qwen_app::NativeAllocatorBudget qwen_native_allocator_budget(std::uint64_t) { throw std::runtime_error("Native allocator observation is unavailable"); }
void qwen_native_gpu_initialize(const char *) { throw std::runtime_error("Native platform frontend is not linked"); }
extern "C" void qwen_native_driver_begin() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_complete() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_checkpoint() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_retain() {}
extern "C" void qwen_native_driver_before_submit() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_after_submit() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_register_device(std::uintptr_t) { qwen_native_halt("native_platform_frontend_not_linked"); }
#endif
