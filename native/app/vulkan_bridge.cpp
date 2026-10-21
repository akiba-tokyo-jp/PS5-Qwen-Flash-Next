// SPDX-License-Identifier: MIT
// Static Vulkan entry points forward directly to the pinned RADV implementation.
// No feature, precision, synchronization or allocation policy is changed here.
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <cstdint>
#include <cstring>

extern "C" {
PFN_vkVoidFunction vk_icdGetInstanceProcAddr(VkInstance, const char *);
PFN_vkVoidFunction vk_common_GetDeviceProcAddr(VkDevice, const char *);
void vk_common_GetPhysicalDeviceFeatures2(VkPhysicalDevice, VkPhysicalDeviceFeatures2 *);
void vk_common_CmdCopyBuffer(VkCommandBuffer, VkBuffer, VkBuffer, std::uint32_t, const VkBufferCopy *);

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetDeviceProcAddr(VkDevice device, const char * name) {
    if (!name) return nullptr;
    if (std::strcmp(name, "vkGetDeviceProcAddr") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(vkGetDeviceProcAddr);
    return vk_common_GetDeviceProcAddr(device, name);
}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetInstanceProcAddr(VkInstance instance, const char * name) {
    if (!name) return nullptr;
    if (std::strcmp(name, "vkGetInstanceProcAddr") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(vkGetInstanceProcAddr);
    if (std::strcmp(name, "vkGetDeviceProcAddr") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(vkGetDeviceProcAddr);
    return vk_icdGetInstanceProcAddr(instance, name);
}

VKAPI_ATTR void VKAPI_CALL vkGetPhysicalDeviceFeatures2(VkPhysicalDevice physical, VkPhysicalDeviceFeatures2 * features) {
    vk_common_GetPhysicalDeviceFeatures2(physical, features);
}

VKAPI_ATTR void VKAPI_CALL vkCmdCopyBuffer(VkCommandBuffer command, VkBuffer source, VkBuffer destination,
                                         std::uint32_t count, const VkBufferCopy * regions) {
    vk_common_CmdCopyBuffer(command, source, destination, count, regions);
}
}
