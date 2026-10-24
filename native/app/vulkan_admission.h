// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
namespace qwen_app {
struct VulkanDiscovery { std::uint32_t api_version = 0, instance_extensions = 0; };
// Global CPU-side queries only. Does not create a Vulkan instance/device,
// register a backend, allocate GPU memory or submit commands.
VulkanDiscovery inspect_vulkan_globals();
}
