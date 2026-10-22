// SPDX-License-Identifier: MIT
#include "native_gpu.h"
#include "driver_lifecycle.h"
#include <stdexcept>
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
void qwen_native_gpu_initialize(const char *) { throw std::runtime_error("Native platform frontend is not linked"); }
extern "C" void qwen_native_driver_begin() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_complete() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_checkpoint() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_retain() {}
extern "C" void qwen_native_driver_before_submit() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_after_submit() { qwen_native_halt("native_platform_frontend_not_linked"); }
extern "C" void qwen_native_driver_register_device(std::uintptr_t) { qwen_native_halt("native_platform_frontend_not_linked"); }
#endif
