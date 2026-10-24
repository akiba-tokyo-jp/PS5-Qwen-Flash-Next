// SPDX-License-Identifier: MIT
// Link/API forwarding checks only. No driver or GPU is loaded.
#include <vulkan/vulkan.h>
#include <cstring>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include "../native/app/vulkan_admission.h"

static int instance_calls = 0, device_calls = 0, feature_calls = 0, copies = 0;
static VkInstance instance = reinterpret_cast<VkInstance>(1);
static VkDevice device = reinterpret_cast<VkDevice>(2);
static VkPhysicalDevice physical = reinterpret_cast<VkPhysicalDevice>(3);
static VkCommandBuffer command = reinterpret_cast<VkCommandBuffer>(4);
static VkPhysicalDeviceFeatures2 * expected_features;
static const VkBufferCopy * expected_regions;
static void check(bool value) { if (!value) throw std::runtime_error("Vulkan bridge changed an API argument"); }
static void sentinel() {}
static VkResult wait_result = VK_SUCCESS, submit_result = VK_SUCCESS;
static std::uint64_t received_timeout = 0;
static int waits = 0, submits = 0;
static bool globals_available = true;
static VkResult global_result = VK_SUCCESS;
static int global_creates = 0, global_queries = 0, phases = 0;
static int device_creates=0, registered_devices=0, submit_hooks=0, submits2=0;
static bool submit2_available=true;
static VkResult VKAPI_CALL fake_create_device(VkPhysicalDevice value,const VkDeviceCreateInfo * info,
                                             const VkAllocationCallbacks * allocator,VkDevice * output) {
    check(value==physical&&!info&&!allocator);++device_creates;*output=device;return global_result;
}
static VkResult VKAPI_CALL fake_submit2(VkQueue value,std::uint32_t count,const VkSubmitInfo2 * info,VkFence fence) {
    check(value==VK_NULL_HANDLE&&count==1&&!info&&fence==VK_NULL_HANDLE);++submits2;return submit_result;
}
static VkResult VKAPI_CALL fake_version(std::uint32_t * value) { ++global_queries;*value=VK_API_VERSION_1_3;return global_result; }
static VkResult VKAPI_CALL fake_extensions(const char * layer,std::uint32_t * count,VkExtensionProperties * values) {
    check(!layer&&!values);++global_queries;*count=3;return global_result;
}
static VkResult VKAPI_CALL fake_create_instance(const VkInstanceCreateInfo * info,const VkAllocationCallbacks * allocator,VkInstance * value) {
    check(!info&&!allocator);++global_creates;*value=instance;return global_result;
}
struct Halt : std::runtime_error { using std::runtime_error::runtime_error; };
static VkResult VKAPI_CALL fake_wait_fences(VkDevice value, std::uint32_t count, const VkFence * fences,
                                           VkBool32 all, std::uint64_t timeout) {
    check(value == device && count == 1 && !fences && all == VK_TRUE);
    received_timeout = timeout; ++waits; return wait_result;
}
static VkResult VKAPI_CALL fake_wait_semaphores(VkDevice value, const VkSemaphoreWaitInfo * info, std::uint64_t timeout) {
    check(value == device && !info); received_timeout = timeout; ++waits; return wait_result;
}
extern "C" {
[[noreturn]] void qwen_native_halt(const char * operation) { throw Halt(operation); }
void qwen_native_stage(const char *) { ++phases; }
void qwen_native_driver_register_device(std::uintptr_t value) {check(value==reinterpret_cast<std::uintptr_t>(device));++registered_devices;}
void qwen_native_driver_before_submit() {++submit_hooks;}
PFN_vkVoidFunction vk_icdGetInstanceProcAddr(VkInstance value, const char * name) {
    if (!value) {
        if(!globals_available)return nullptr;
        if(!std::strcmp(name,"vkEnumerateInstanceVersion"))return reinterpret_cast<PFN_vkVoidFunction>(fake_version);
        if(!std::strcmp(name,"vkEnumerateInstanceExtensionProperties"))return reinterpret_cast<PFN_vkVoidFunction>(fake_extensions);
        if(!std::strcmp(name,"vkCreateInstance"))return reinterpret_cast<PFN_vkVoidFunction>(fake_create_instance);
        check(false);
    }
    check(value == instance && !std::strcmp(name, "vkCreateDevice")); ++instance_calls;
    return reinterpret_cast<PFN_vkVoidFunction>(fake_create_device);
}
PFN_vkVoidFunction vk_common_GetDeviceProcAddr(VkDevice value, const char * name) {
    check(value == device);
    if (!std::strcmp(name, "vkWaitForFences")) return reinterpret_cast<PFN_vkVoidFunction>(fake_wait_fences);
    if (!std::strcmp(name, "vkWaitSemaphores")) return reinterpret_cast<PFN_vkVoidFunction>(fake_wait_semaphores);
    if(!std::strcmp(name,"vkQueueSubmit2")||!std::strcmp(name,"vkQueueSubmit2KHR"))
        return submit2_available?reinterpret_cast<PFN_vkVoidFunction>(fake_submit2):nullptr;
    check(!std::strcmp(name, "vkCreateBuffer")); ++device_calls; return sentinel;
}
VkResult vk_common_QueueSubmit(VkQueue value, std::uint32_t count, const VkSubmitInfo * info, VkFence fence) {
    check(value == VK_NULL_HANDLE && count == 1 && !info && fence == VK_NULL_HANDLE); ++submits; return submit_result;
}
void vk_common_GetPhysicalDeviceFeatures2(VkPhysicalDevice value, VkPhysicalDeviceFeatures2 * features) {
    check(value == physical && features == expected_features); ++feature_calls;
    features->features.shaderInt64 = VK_TRUE;
}
void vk_common_CmdCopyBuffer(VkCommandBuffer value, VkBuffer source, VkBuffer destination,
                             uint32_t count, const VkBufferCopy * regions) {
    check(value == command && source == VK_NULL_HANDLE && destination == VK_NULL_HANDLE && count == 1 && regions == expected_regions);
    ++copies;
}
}
int main() {
    try {
        const auto create_device=reinterpret_cast<PFN_vkCreateDevice>(vkGetInstanceProcAddr(instance,"vkCreateDevice"));
        VkDevice created_device=nullptr;
        check(create_device(physical,nullptr,nullptr,&created_device)==VK_SUCCESS&&created_device==device&&registered_devices==1&&device_creates==1);
        global_result=VK_ERROR_INITIALIZATION_FAILED;
        check(create_device(physical,nullptr,nullptr,&created_device)==global_result&&registered_devices==1&&device_creates==2);
        global_result=VK_SUCCESS;
        check(vkGetDeviceProcAddr(device, "vkCreateBuffer") == sentinel);
        check(vkGetInstanceProcAddr(VK_NULL_HANDLE, "vkGetInstanceProcAddr") == reinterpret_cast<PFN_vkVoidFunction>(vkGetInstanceProcAddr));
        check(vkGetInstanceProcAddr(instance, "vkGetDeviceProcAddr") == reinterpret_cast<PFN_vkVoidFunction>(vkGetDeviceProcAddr));
        check(vkGetDeviceProcAddr(device, "vkGetDeviceProcAddr") == reinterpret_cast<PFN_vkVoidFunction>(vkGetDeviceProcAddr));
        check(!vkGetInstanceProcAddr(instance, nullptr) && !vkGetDeviceProcAddr(device, nullptr));
        VkPhysicalDeviceFeatures2 features{}; expected_features = &features;
        vkGetPhysicalDeviceFeatures2(physical, &features);
        check(features.features.shaderInt64 == VK_TRUE);
        VkBufferCopy region{1, 2, 3}; expected_regions = &region;
        vkCmdCopyBuffer(command, VK_NULL_HANDLE, VK_NULL_HANDLE, 1, &region);
        check(instance_calls == 1 && device_calls == 1 && feature_calls == 1 && copies == 1);
        const auto fences = reinterpret_cast<PFN_vkWaitForFences>(vkGetDeviceProcAddr(device, "vkWaitForFences"));
        check(reinterpret_cast<PFN_vkVoidFunction>(fences) == vkGetInstanceProcAddr(instance, "vkWaitForFences"));
        check(fences(device, 1, nullptr, VK_TRUE, UINT64_MAX) == VK_SUCCESS && received_timeout == 10'000'000'000ULL);
        wait_result = VK_TIMEOUT;
        check(fences(device, 1, nullptr, VK_TRUE, 0) == VK_TIMEOUT && received_timeout == 0);
        bool halted = false;
        try { fences(device, 1, nullptr, VK_TRUE, UINT64_MAX); } catch (const Halt &) { halted = true; }
        check(halted);
        wait_result = VK_ERROR_DEVICE_LOST; halted = false;
        try { fences(device, 1, nullptr, VK_TRUE, 1); } catch (const Halt &) { halted = true; }
        check(halted);
        const auto semaphore = reinterpret_cast<PFN_vkWaitSemaphores>(vkGetDeviceProcAddr(device, "vkWaitSemaphoresKHR"));
        wait_result = VK_SUCCESS;
        check(semaphore(device, nullptr, UINT64_MAX) == VK_SUCCESS && received_timeout == 10'000'000'000ULL);
        wait_result = VK_TIMEOUT; halted = false;
        try { semaphore(device, nullptr, UINT64_MAX); } catch (const Halt &) { halted = true; }
        check(halted && waits == 6);
        const auto submit = reinterpret_cast<PFN_vkQueueSubmit>(vkGetDeviceProcAddr(device, "vkQueueSubmit"));
        check(submit(VK_NULL_HANDLE, 1, nullptr, VK_NULL_HANDLE) == VK_SUCCESS);
        submit_result = VK_ERROR_DEVICE_LOST; halted = false;
        try { submit(VK_NULL_HANDLE, 1, nullptr, VK_NULL_HANDLE); } catch (const Halt &) { halted = true; }
        check(halted && submits == 2&&submit_hooks==2);
        const auto submit2=reinterpret_cast<PFN_vkQueueSubmit2>(vkGetDeviceProcAddr(device,"vkQueueSubmit2KHR"));
        submit_result=VK_SUCCESS;check(submit2(nullptr,1,nullptr,VK_NULL_HANDLE)==VK_SUCCESS&&submits2==1&&submit_hooks==3);
        submit_result=VK_ERROR_DEVICE_LOST;halted=false;
        try{submit2(nullptr,1,nullptr,VK_NULL_HANDLE);}catch(const Halt&){halted=true;}
        check(halted&&submits2==2&&submit_hooks==4);
        submit2_available=false;check(!vkGetDeviceProcAddr(device,"vkQueueSubmit2"));
        phases=0;
        const auto discovery=qwen_app::inspect_vulkan_globals();
        check(discovery.api_version==VK_API_VERSION_1_3&&discovery.instance_extensions==3&&global_queries==2&&global_creates==0&&phases==4);
        globals_available=false;
        check(!vkGetInstanceProcAddr(nullptr,"vkCreateInstance"));
        bool rejected=false;
        try{qwen_app::inspect_vulkan_globals();}catch(const std::runtime_error &){rejected=true;}
        check(rejected&&global_queries==2&&global_creates==0);
        globals_available=true;global_result=VK_ERROR_INITIALIZATION_FAILED;rejected=false;
        try{qwen_app::inspect_vulkan_globals();}catch(const std::runtime_error &){rejected=true;}
        check(rejected&&global_queries==3&&global_creates==0);
        global_result=VK_SUCCESS;
        const auto create=reinterpret_cast<PFN_vkCreateInstance>(vkGetInstanceProcAddr(nullptr,"vkCreateInstance"));
        VkInstance created=nullptr;check(create(nullptr,nullptr,&created)==VK_SUCCESS&&created==instance&&global_creates==1);
        std::cout << "Static forwarding, bounded waits, preserved polling and halt-before-unwind on failed submit/wait passed; API stubs only\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
