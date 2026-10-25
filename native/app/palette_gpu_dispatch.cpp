// SPDX-License-Identifier: MIT
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include "palette_gpu_dispatch.h"
#include "profile_clock.h"
#include <array>
#include <cstring>
#include <stdexcept>
extern "C" {
PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance,const char *);
PFN_vkVoidFunction vkGetDeviceProcAddr(VkDevice,const char *);
void qwen_native_stage(const char *);
[[noreturn]] void qwen_native_halt(const char *);
}
namespace qwen_app {
namespace {
void require(bool value,const char *phase) {
    if(!value)qwen_native_halt(phase);
}
template<class T>T instance_fn(VkInstance instance,const char *name) {
    const auto fn=reinterpret_cast<T>(vkGetInstanceProcAddr(instance,name));
    require(fn!=nullptr,"palette_missing_instance_function");return fn;
}
template<class T>T device_fn(VkDevice device,const char *name) {
    const auto fn=reinterpret_cast<T>(vkGetDeviceProcAddr(device,name));
    require(fn!=nullptr,"palette_missing_device_function");return fn;
}
std::uint64_t now_ns() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(ProfileClock::now().time_since_epoch()).count();
}
}
struct PaletteGpuDispatch::State {
    VkInstance instance=VK_NULL_HANDLE;VkPhysicalDevice physical=VK_NULL_HANDLE;
    VkDevice device=VK_NULL_HANDLE;VkQueue queue=VK_NULL_HANDLE;
    VkPhysicalDeviceMemoryProperties properties{};
    VkDescriptorSetLayout descriptor_layout=VK_NULL_HANDLE;
    VkPipelineLayout layout=VK_NULL_HANDLE;VkDescriptorPool descriptor_pool=VK_NULL_HANDLE;
    VkDescriptorSet descriptor=VK_NULL_HANDLE;VkCommandPool command_pool=VK_NULL_HANDLE;
    VkCommandBuffer command=VK_NULL_HANDLE;VkFence fence=VK_NULL_HANDLE;
    std::array<VkPipeline,2> pipelines{};
    std::array<VkBuffer,2> buffers{};std::array<VkDeviceMemory,2> memory{};
    std::array<void *,2> mapped{};
    std::uint64_t allocated_bytes=0;bool completed=true;
#define DEVICE_API(X) \
    X(CreateBuffer) X(GetBufferMemoryRequirements) X(AllocateMemory) X(BindBufferMemory) X(MapMemory) \
    X(CreateDescriptorSetLayout) X(CreatePipelineLayout) X(CreateShaderModule) X(CreateComputePipelines) \
    X(CreateDescriptorPool) X(AllocateDescriptorSets) X(UpdateDescriptorSets) X(CreateCommandPool) \
    X(AllocateCommandBuffers) X(CreateFence) X(ResetFences) X(ResetCommandBuffer) X(BeginCommandBuffer) \
    X(CmdPipelineBarrier) X(CmdBindPipeline) X(CmdBindDescriptorSets) X(CmdPushConstants) X(CmdDispatch) \
    X(EndCommandBuffer) X(QueueSubmit) X(WaitForFences)
#define MEMBER(name) PFN_vk##name name=nullptr;
    DEVICE_API(MEMBER)
#undef MEMBER
};
PaletteGpuDispatch::PaletteGpuDispatch(const std::uint32_t *copy,std::size_t copy_bytes,
        const std::uint32_t *palette,std::size_t palette_bytes):state_(new State) {
    require(copy&&palette&&copy_bytes>=20&&palette_bytes>=20&&copy_bytes%4==0&&palette_bytes%4==0&&
        copy_bytes<=65536&&palette_bytes<=65536&&copy[0]==0x07230203&&palette[0]==0x07230203,
        "palette_invalid_verified_SPIRV_bounds");
    auto &s=*state_;
    VkApplicationInfo app{};app.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO;app.pApplicationName="Qwen palette diagnostic";app.apiVersion=VK_API_VERSION_1_2;
    VkInstanceCreateInfo info{};info.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;info.pApplicationInfo=&app;
    qwen_native_stage("palette_before_instance_creation");
    require(instance_fn<PFN_vkCreateInstance>(VK_NULL_HANDLE,"vkCreateInstance")(&info,nullptr,&s.instance)==VK_SUCCESS,"palette_instance_creation_failed");
    std::uint32_t count=0;auto enumerate=instance_fn<PFN_vkEnumeratePhysicalDevices>(s.instance,"vkEnumeratePhysicalDevices");
    require(enumerate(s.instance,&count,nullptr)==VK_SUCCESS&&count>0&&count<=8,"palette_physical_device_count_failed");
    std::array<VkPhysicalDevice,8> physical{};require(enumerate(s.instance,&count,physical.data())==VK_SUCCESS&&count>0&&count<=8,"palette_physical_device_query_failed");s.physical=physical[0];
    auto families=instance_fn<PFN_vkGetPhysicalDeviceQueueFamilyProperties>(s.instance,"vkGetPhysicalDeviceQueueFamilyProperties");
    count=0;families(s.physical,&count,nullptr);require(count>0&&count<=32,"palette_queue_family_count_failed");
    std::array<VkQueueFamilyProperties,32> queues{};families(s.physical,&count,queues.data());
    require(count>0&&count<=32,"palette_queue_family_bounds_failed");std::uint32_t family=count;
    for(std::uint32_t i=0;i<count;++i)if(queues[i].queueCount&&(queues[i].queueFlags&VK_QUEUE_COMPUTE_BIT)){family=i;break;}
    require(family<count,"palette_compute_queue_missing");
    const float priority=0.0f;VkDeviceQueueCreateInfo queue{};queue.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue.queueFamilyIndex=family;queue.queueCount=1;queue.pQueuePriorities=&priority;
    VkDeviceCreateInfo device{};device.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;device.queueCreateInfoCount=1;device.pQueueCreateInfos=&queue;
    // The existing bridge registers exactly this one device and all submissions.
    require(instance_fn<PFN_vkCreateDevice>(s.instance,"vkCreateDevice")(s.physical,&device,nullptr,&s.device)==VK_SUCCESS,"palette_device_creation_failed");
#define LOAD(name) s.name=device_fn<PFN_vk##name>(s.device,"vk" #name);
    DEVICE_API(LOAD)
#undef LOAD
    device_fn<PFN_vkGetDeviceQueue>(s.device,"vkGetDeviceQueue")(s.device,family,0,&s.queue);
    require(s.queue!=VK_NULL_HANDLE,"palette_queue_missing");
    instance_fn<PFN_vkGetPhysicalDeviceMemoryProperties>(s.instance,"vkGetPhysicalDeviceMemoryProperties")(s.physical,&s.properties);
    require(s.properties.memoryTypeCount>0&&s.properties.memoryTypeCount<=VK_MAX_MEMORY_TYPES,"palette_memory_type_bounds_failed");
    for(unsigned i=0;i<2;++i) {
        VkBufferCreateInfo b{};b.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;b.size=buffer_bytes;b.usage=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;b.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
        require(s.CreateBuffer(s.device,&b,nullptr,&s.buffers[i])==VK_SUCCESS,"palette_buffer_creation_failed");
        VkMemoryRequirements r{};s.GetBufferMemoryRequirements(s.device,s.buffers[i],&r);
        require(r.size>=buffer_bytes&&r.size<=8u<<20&&r.alignment&&r.memoryTypeBits,"palette_memory_requirement_bounds_failed");
        unsigned type=s.properties.memoryTypeCount;
        for(unsigned j=0;j<s.properties.memoryTypeCount;++j)if((r.memoryTypeBits&(1u<<j))&&
            (s.properties.memoryTypes[j].propertyFlags&(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))==
                (VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)){type=j;break;}
        require(type<s.properties.memoryTypeCount,"palette_coherent_memory_type_missing");
        VkMemoryAllocateInfo allocation{};allocation.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;allocation.allocationSize=r.size;allocation.memoryTypeIndex=type;
        require(s.AllocateMemory(s.device,&allocation,nullptr,&s.memory[i])==VK_SUCCESS,"palette_memory_allocation_failed");
        s.allocated_bytes+=r.size;require(s.allocated_bytes<=16u<<20,"palette_total_allocation_bound_failed");
        require(s.BindBufferMemory(s.device,s.buffers[i],s.memory[i],0)==VK_SUCCESS,"palette_buffer_binding_failed");
        require(s.MapMemory(s.device,s.memory[i],0,r.size,0,&s.mapped[i])==VK_SUCCESS&&s.mapped[i]&&
            reinterpret_cast<std::uintptr_t>(s.mapped[i])%16384==0,"palette_owned_mapping_alignment_failed");
    }
    std::array<VkDescriptorSetLayoutBinding,2> bindings{};
    for(unsigned i=0;i<2;++i){bindings[i].binding=i;bindings[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;bindings[i].descriptorCount=1;bindings[i].stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;}
    VkDescriptorSetLayoutCreateInfo dl{};dl.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO;dl.bindingCount=2;dl.pBindings=bindings.data();
    require(s.CreateDescriptorSetLayout(s.device,&dl,nullptr,&s.descriptor_layout)==VK_SUCCESS,"palette_descriptor_layout_failed");
    VkPushConstantRange range{};range.stageFlags=VK_SHADER_STAGE_COMPUTE_BIT;range.size=8;
    VkPipelineLayoutCreateInfo pl{};pl.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;pl.setLayoutCount=1;pl.pSetLayouts=&s.descriptor_layout;pl.pushConstantRangeCount=1;pl.pPushConstantRanges=&range;
    require(s.CreatePipelineLayout(s.device,&pl,nullptr,&s.layout)==VK_SUCCESS,"palette_pipeline_layout_failed");
    const std::array<const std::uint32_t *,2> words{copy,palette};const std::array<std::size_t,2> sizes{copy_bytes,palette_bytes};
    for(unsigned i=0;i<2;++i) {
        VkShaderModuleCreateInfo sm{};sm.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;sm.codeSize=sizes[i];sm.pCode=words[i];VkShaderModule module=VK_NULL_HANDLE;
        require(s.CreateShaderModule(s.device,&sm,nullptr,&module)==VK_SUCCESS,"palette_shader_module_failed");
        VkComputePipelineCreateInfo cp{};cp.sType=VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO;cp.layout=s.layout;
        cp.stage.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;cp.stage.stage=VK_SHADER_STAGE_COMPUTE_BIT;cp.stage.module=module;cp.stage.pName="main";
        qwen_native_stage("palette_before_pipeline_creation");
        require(s.CreateComputePipelines(s.device,VK_NULL_HANDLE,1,&cp,nullptr,&s.pipelines[i])==VK_SUCCESS,"palette_pipeline_creation_failed");
    }
    VkDescriptorPoolSize ps{};ps.type=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;ps.descriptorCount=2;
    VkDescriptorPoolCreateInfo dp{};dp.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO;dp.maxSets=1;dp.poolSizeCount=1;dp.pPoolSizes=&ps;
    require(s.CreateDescriptorPool(s.device,&dp,nullptr,&s.descriptor_pool)==VK_SUCCESS,"palette_descriptor_pool_failed");
    VkDescriptorSetAllocateInfo da{};da.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO;da.descriptorPool=s.descriptor_pool;da.descriptorSetCount=1;da.pSetLayouts=&s.descriptor_layout;
    require(s.AllocateDescriptorSets(s.device,&da,&s.descriptor)==VK_SUCCESS,"palette_descriptor_allocation_failed");
    std::array<VkDescriptorBufferInfo,2> bi{};std::array<VkWriteDescriptorSet,2> writes{};
    for(unsigned i=0;i<2;++i){bi[i]={s.buffers[i],0,buffer_bytes};writes[i].sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET;writes[i].dstSet=s.descriptor;writes[i].dstBinding=i;writes[i].descriptorCount=1;writes[i].descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;writes[i].pBufferInfo=&bi[i];}
    s.UpdateDescriptorSets(s.device,2,writes.data(),0,nullptr);
    VkCommandPoolCreateInfo pool{};pool.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;pool.flags=VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;pool.queueFamilyIndex=family;
    require(s.CreateCommandPool(s.device,&pool,nullptr,&s.command_pool)==VK_SUCCESS,"palette_command_pool_failed");
    VkCommandBufferAllocateInfo ca{};ca.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;ca.commandPool=s.command_pool;ca.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;ca.commandBufferCount=1;
    require(s.AllocateCommandBuffers(s.device,&ca,&s.command)==VK_SUCCESS,"palette_command_allocation_failed");
    VkFenceCreateInfo fi{};fi.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    require(s.CreateFence(s.device,&fi,nullptr,&s.fence)==VK_SUCCESS,"palette_fence_creation_failed");
    qwen_native_stage("palette_owned_buffers_and_pipelines_ready");
}
unsigned char *PaletteGpuDispatch::source(){return static_cast<unsigned char *>(state_->mapped[0]);}
unsigned char *PaletteGpuDispatch::target(){return static_cast<unsigned char *>(state_->mapped[1]);}
std::uint64_t PaletteGpuDispatch::dispatch(bool palette,std::uint32_t values,std::uint32_t encoded_bytes) {
    auto &s=*state_;
    require(s.completed&&values&&values%64==0&&std::uint64_t(values)*2<=buffer_bytes-16&&
        encoded_bytes&&encoded_bytes<=buffer_bytes,"palette_dispatch_bounds_or_lifetime_failed");
    const auto started=now_ns();require(started!=0,"palette_dispatch_clock_failed");
    require(s.ResetFences(s.device,1,&s.fence)==VK_SUCCESS,"palette_fence_reset_failed");
    require(s.ResetCommandBuffer(s.command,0)==VK_SUCCESS,"palette_command_reset_failed");
    VkCommandBufferBeginInfo begin{};begin.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    require(s.BeginCommandBuffer(s.command,&begin)==VK_SUCCESS,"palette_command_begin_failed");
    VkMemoryBarrier barrier{};barrier.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER;barrier.srcAccessMask=VK_ACCESS_HOST_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_SHADER_READ_BIT|VK_ACCESS_SHADER_WRITE_BIT;
    s.CmdPipelineBarrier(s.command,VK_PIPELINE_STAGE_HOST_BIT,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,0,1,&barrier,0,nullptr,0,nullptr);
    s.CmdBindPipeline(s.command,VK_PIPELINE_BIND_POINT_COMPUTE,s.pipelines[palette?1:0]);
    s.CmdBindDescriptorSets(s.command,VK_PIPELINE_BIND_POINT_COMPUTE,s.layout,0,1,&s.descriptor,0,nullptr);
    const std::array<std::uint32_t,2> limits{values,encoded_bytes};
    s.CmdPushConstants(s.command,s.layout,VK_SHADER_STAGE_COMPUTE_BIT,0,sizeof(limits),limits.data());
    s.CmdDispatch(s.command,(values/2+255)/256,1,1);
    barrier.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT;barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
    s.CmdPipelineBarrier(s.command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&barrier,0,nullptr,0,nullptr);
    require(s.EndCommandBuffer(s.command)==VK_SUCCESS,"palette_command_end_failed");
    VkSubmitInfo submit{};submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;submit.commandBufferCount=1;submit.pCommandBuffers=&s.command;
    qwen_native_stage("palette_before_queue_submit");s.completed=false;
    require(s.QueueSubmit(s.queue,1,&submit,s.fence)==VK_SUCCESS,"palette_queue_submit_failed");
    qwen_native_stage("palette_queue_submit_returned_before_fence");
    require(s.WaitForFences(s.device,1,&s.fence,VK_TRUE,2000000000ull)==VK_SUCCESS,"palette_fence_completion_uncertain_backing_retained");
    s.completed=true;qwen_native_stage("palette_fence_positively_completed");
    const auto ended=now_ns();require(ended>=started,"palette_dispatch_clock_regressed");return ended-started;
}
#undef DEVICE_API
}
