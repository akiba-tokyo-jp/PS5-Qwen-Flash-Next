// SPDX-License-Identifier: MIT
#include "vulkan_admission.h"
#include <vulkan/vulkan.h>
#include <stdexcept>
namespace qwen_app {
VulkanDiscovery inspect_vulkan_globals() {
    const auto version = reinterpret_cast<PFN_vkEnumerateInstanceVersion>(vkGetInstanceProcAddr(nullptr,"vkEnumerateInstanceVersion"));
    const auto extensions = reinterpret_cast<PFN_vkEnumerateInstanceExtensionProperties>(vkGetInstanceProcAddr(nullptr,"vkEnumerateInstanceExtensionProperties"));
    if (!version || !extensions || !vkGetInstanceProcAddr(nullptr,"vkCreateInstance"))
        throw std::runtime_error("Required static Vulkan global entry points are unavailable");
    VulkanDiscovery result;
    if (version(&result.api_version) != VK_SUCCESS || result.api_version < VK_API_VERSION_1_2)
        throw std::runtime_error("The static Vulkan provider does not admit Vulkan 1.2");
    if (extensions(nullptr,&result.instance_extensions,nullptr) != VK_SUCCESS || result.instance_extensions > 1024)
        throw std::runtime_error("Static Vulkan instance extension enumeration failed its bound");
    return result;
}
}
