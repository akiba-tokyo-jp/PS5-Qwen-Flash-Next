// SPDX-License-Identifier: MIT
// Link/API forwarding checks only. No driver or GPU is loaded.
#include <vulkan/vulkan.h>
#include <cstring>
#include <cstdint>
#include <iostream>
#include <stdexcept>

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
PFN_vkVoidFunction vk_icdGetInstanceProcAddr(VkInstance value, const char * name) {
    check(value == instance && !std::strcmp(name, "vkCreateDevice")); ++instance_calls; return sentinel;
}
PFN_vkVoidFunction vk_common_GetDeviceProcAddr(VkDevice value, const char * name) {
    check(value == device);
    if (!std::strcmp(name, "vkWaitForFences")) return reinterpret_cast<PFN_vkVoidFunction>(fake_wait_fences);
    if (!std::strcmp(name, "vkWaitSemaphores")) return reinterpret_cast<PFN_vkVoidFunction>(fake_wait_semaphores);
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
        check(vkGetInstanceProcAddr(instance, "vkCreateDevice") == sentinel);
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
        check(halted && submits == 2);
        std::cout << "Static forwarding, bounded waits, preserved polling and halt-before-unwind on failed submit/wait passed; API stubs only\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
