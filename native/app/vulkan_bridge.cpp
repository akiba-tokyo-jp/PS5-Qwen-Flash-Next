// SPDX-License-Identifier: MIT
// Static Vulkan entry points forward directly to the pinned RADV implementation.
// Feature and precision queries remain unchanged. Client blocking waits have a
// finite ceiling; a failed wait halts without unwinding or reusing resources.
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include <cstdint>
#include <cstring>
#include <algorithm>

extern "C" {
PFN_vkVoidFunction vk_icdGetInstanceProcAddr(VkInstance, const char *);
PFN_vkVoidFunction vk_common_GetDeviceProcAddr(VkDevice, const char *);
void vk_common_GetPhysicalDeviceFeatures2(VkPhysicalDevice, VkPhysicalDeviceFeatures2 *);
void vk_common_CmdCopyBuffer(VkCommandBuffer, VkBuffer, VkBuffer, std::uint32_t, const VkBufferCopy *);
VkResult vk_common_QueueSubmit(VkQueue, std::uint32_t, const VkSubmitInfo *, VkFence);
[[noreturn]] void qwen_native_halt(const char *);
void qwen_native_stage(const char *);
void ggml_app_backend_phase(const char * value) { qwen_native_stage(value); }

static VkResult VKAPI_CALL checked_instance_version(std::uint32_t * version) {
    auto operation = reinterpret_cast<PFN_vkEnumerateInstanceVersion>(vk_icdGetInstanceProcAddr(nullptr,"vkEnumerateInstanceVersion"));
    if (!operation) qwen_native_halt("missing_instance_version_entrypoint");
    qwen_native_stage("Vulkan_before_global_version_query");
    const auto result = operation(version);
    qwen_native_stage(result == VK_SUCCESS ? "Vulkan_global_version_query_completed" : "Vulkan_global_version_query_failed");
    return result;
}
static VkResult VKAPI_CALL checked_instance_extensions(const char * layer, std::uint32_t * count, VkExtensionProperties * properties) {
    auto operation = reinterpret_cast<PFN_vkEnumerateInstanceExtensionProperties>(vk_icdGetInstanceProcAddr(nullptr,"vkEnumerateInstanceExtensionProperties"));
    if (!operation) qwen_native_halt("missing_instance_extensions_entrypoint");
    qwen_native_stage("Vulkan_before_global_extension_query");
    const auto result = operation(layer,count,properties);
    qwen_native_stage(result == VK_SUCCESS ? "Vulkan_global_extension_query_completed" : "Vulkan_global_extension_query_not_success");
    return result;
}
static VkResult VKAPI_CALL checked_create_instance(const VkInstanceCreateInfo * info, const VkAllocationCallbacks * allocator, VkInstance * instance) {
    auto operation = reinterpret_cast<PFN_vkCreateInstance>(vk_icdGetInstanceProcAddr(nullptr,"vkCreateInstance"));
    if (!operation) qwen_native_halt("missing_create_instance_entrypoint");
    qwen_native_stage("Vulkan_before_instance_creation");
    const auto result = operation(info,allocator,instance);
    qwen_native_stage(result == VK_SUCCESS ? "Vulkan_instance_creation_completed" : "Vulkan_instance_creation_failed");
    return result;
}

static constexpr std::uint64_t wait_limit_ns = 10'000'000'000ULL;
static VkResult VKAPI_CALL bounded_wait_fences(VkDevice device, std::uint32_t count, const VkFence * fences,
                                             VkBool32 all, std::uint64_t timeout) {
    auto operation = reinterpret_cast<PFN_vkWaitForFences>(vk_common_GetDeviceProcAddr(device, "vkWaitForFences"));
    if (!operation) qwen_native_halt("missing_wait_for_fences");
    const auto result = operation(device, count, fences, all, std::min(timeout, wait_limit_ns));
    if ((result == VK_TIMEOUT && timeout > wait_limit_ns) || result < 0)
        qwen_native_halt("wait_for_fences_failed");
    return result;
}
static VkResult VKAPI_CALL bounded_wait_semaphores(VkDevice device, const VkSemaphoreWaitInfo * info, std::uint64_t timeout) {
    auto operation = reinterpret_cast<PFN_vkWaitSemaphores>(vk_common_GetDeviceProcAddr(device, "vkWaitSemaphores"));
    if (!operation) qwen_native_halt("missing_wait_semaphores");
    const auto result = operation(device, info, std::min(timeout, wait_limit_ns));
    if ((result == VK_TIMEOUT && timeout > wait_limit_ns) || result < 0)
        qwen_native_halt("wait_semaphores_failed");
    return result;
}
static VkResult VKAPI_CALL checked_queue_submit(VkQueue queue, std::uint32_t count, const VkSubmitInfo * submits, VkFence fence) {
    const auto result = vk_common_QueueSubmit(queue, count, submits, fence);
    if (result != VK_SUCCESS) qwen_native_halt("queue_submit_failed");
    return result;
}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetDeviceProcAddr(VkDevice device, const char * name) {
    if (!name) return nullptr;
    if (std::strcmp(name, "vkGetDeviceProcAddr") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(vkGetDeviceProcAddr);
    if (std::strcmp(name, "vkWaitForFences") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(bounded_wait_fences);
    if (std::strcmp(name, "vkWaitSemaphores") == 0 || std::strcmp(name, "vkWaitSemaphoresKHR") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(bounded_wait_semaphores);
    if (std::strcmp(name, "vkQueueSubmit") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(checked_queue_submit);
    return vk_common_GetDeviceProcAddr(device, name);
}

VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL vkGetInstanceProcAddr(VkInstance instance, const char * name) {
    if (!name) return nullptr;
    if (std::strcmp(name, "vkGetInstanceProcAddr") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(vkGetInstanceProcAddr);
    // Resolve availability first; a missing global must remain null for the
    // caller's explicit capability guard rather than become a callable wrapper.
    if (std::strcmp(name,"vkEnumerateInstanceVersion") == 0)
        return vk_icdGetInstanceProcAddr(nullptr,name) ? reinterpret_cast<PFN_vkVoidFunction>(checked_instance_version) : nullptr;
    if (std::strcmp(name,"vkEnumerateInstanceExtensionProperties") == 0)
        return vk_icdGetInstanceProcAddr(nullptr,name) ? reinterpret_cast<PFN_vkVoidFunction>(checked_instance_extensions) : nullptr;
    if (std::strcmp(name,"vkCreateInstance") == 0)
        return vk_icdGetInstanceProcAddr(nullptr,name) ? reinterpret_cast<PFN_vkVoidFunction>(checked_create_instance) : nullptr;
    if (std::strcmp(name, "vkGetDeviceProcAddr") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(vkGetDeviceProcAddr);
    if (std::strcmp(name, "vkWaitForFences") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(bounded_wait_fences);
    if (std::strcmp(name, "vkWaitSemaphores") == 0 || std::strcmp(name, "vkWaitSemaphoresKHR") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(bounded_wait_semaphores);
    if (std::strcmp(name, "vkQueueSubmit") == 0)
        return reinterpret_cast<PFN_vkVoidFunction>(checked_queue_submit);
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
