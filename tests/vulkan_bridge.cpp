// SPDX-License-Identifier: MIT
// Link/API forwarding checks only. No driver or GPU is loaded.
#include <vulkan/vulkan.h>
#include <cstring>
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
extern "C" {
PFN_vkVoidFunction vk_icdGetInstanceProcAddr(VkInstance value, const char * name) {
    check(value == instance && !std::strcmp(name, "vkCreateDevice")); ++instance_calls; return sentinel;
}
PFN_vkVoidFunction vk_common_GetDeviceProcAddr(VkDevice value, const char * name) {
    check(value == device && !std::strcmp(name, "vkQueueSubmit")); ++device_calls; return sentinel;
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
        check(vkGetDeviceProcAddr(device, "vkQueueSubmit") == sentinel);
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
        std::cout << "Static Vulkan bridge forwarding passed; no GPU calls\n";
    } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
