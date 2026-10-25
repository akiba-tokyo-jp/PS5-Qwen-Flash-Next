// SPDX-License-Identifier: MIT
#define VK_NO_PROTOTYPES
#include <vulkan/vulkan.h>
#include "palette_gpu_dispatch.h"
#include "bf16_palette.h"
#include <array>
#include <cassert>
#include <cstring>
#include <stdexcept>
#include <type_traits>
#include <vector>
using qwen_app::PaletteGpuDispatch;
namespace {
template<class T>T handle(std::uintptr_t value) {
    if constexpr(std::is_pointer_v<T>)return reinterpret_cast<T>(value);
    else return static_cast<T>(value);
}
struct Halt:std::runtime_error{using std::runtime_error::runtime_error;};
alignas(4096)unsigned char source_storage[PaletteGpuDispatch::buffer_bytes+16384];
alignas(4096)unsigned char target_storage[PaletteGpuDispatch::buffer_bytes+16384];
unsigned char *source_bytes=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(source_storage)+16383)&~std::uintptr_t(16383));
unsigned char *target_bytes=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(target_storage)+16383)&~std::uintptr_t(16383));
unsigned resets,submits,waits,barriers,allocations,pipelines,creates,dispatches;
bool timeout_wait=false,coherent=true,oversized=false,fail_submit=false;
std::array<std::uint32_t,4> constants{};VkPipeline bound{};
void reset() {
    resets=submits=waits=barriers=allocations=pipelines=creates=dispatches=0;
    timeout_wait=oversized=fail_submit=false;coherent=true;
}
VkResult VKAPI_CALL fake_CreateInstance(const VkInstanceCreateInfo *info,const VkAllocationCallbacks *,VkInstance *out){++creates;assert(info->enabledLayerCount==0);*out=handle<VkInstance>(1);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_EnumeratePhysicalDevices(VkInstance,std::uint32_t *n,VkPhysicalDevice *out){*n=1;if(out)*out=handle<VkPhysicalDevice>(2);return VK_SUCCESS;}
void VKAPI_CALL fake_GetPhysicalDeviceQueueFamilyProperties(VkPhysicalDevice,std::uint32_t *n,VkQueueFamilyProperties *out){*n=1;if(out){*out={};out->queueCount=1;out->queueFlags=VK_QUEUE_COMPUTE_BIT;}}
VkResult VKAPI_CALL fake_CreateDevice(VkPhysicalDevice,const VkDeviceCreateInfo *info,const VkAllocationCallbacks *,VkDevice *out){assert(info->queueCreateInfoCount==1);*out=handle<VkDevice>(3);return VK_SUCCESS;}
void VKAPI_CALL fake_GetDeviceQueue(VkDevice,std::uint32_t,std::uint32_t,VkQueue *out){*out=handle<VkQueue>(4);}
void VKAPI_CALL fake_GetPhysicalDeviceMemoryProperties(VkPhysicalDevice,VkPhysicalDeviceMemoryProperties *out){*out={};out->memoryTypeCount=1;out->memoryTypes[0].propertyFlags=VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|(coherent?VK_MEMORY_PROPERTY_HOST_COHERENT_BIT:0);}
VkResult VKAPI_CALL fake_CreateBuffer(VkDevice,const VkBufferCreateInfo *info,const VkAllocationCallbacks *,VkBuffer *out){assert(info->size==PaletteGpuDispatch::buffer_bytes);*out=handle<VkBuffer>(5);return VK_SUCCESS;}
void VKAPI_CALL fake_GetBufferMemoryRequirements(VkDevice,VkBuffer,VkMemoryRequirements *out){*out={};out->size=oversized?((8u<<20)+1):PaletteGpuDispatch::buffer_bytes;out->alignment=16384;out->memoryTypeBits=1;}
VkResult VKAPI_CALL fake_AllocateMemory(VkDevice,const VkMemoryAllocateInfo *,const VkAllocationCallbacks *,VkDeviceMemory *out){*out=handle<VkDeviceMemory>(++allocations);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_BindBufferMemory(VkDevice,VkBuffer,VkDeviceMemory,VkDeviceSize offset){assert(offset==0);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_MapMemory(VkDevice,VkDeviceMemory memory,VkDeviceSize,VkDeviceSize,VkMemoryMapFlags,void **out){*out=memory==handle<VkDeviceMemory>(1)?source_bytes:target_bytes;return VK_SUCCESS;}
VkResult VKAPI_CALL fake_CreateDescriptorSetLayout(VkDevice,const VkDescriptorSetLayoutCreateInfo *info,const VkAllocationCallbacks *,VkDescriptorSetLayout *out){assert(info->bindingCount==2);*out=handle<VkDescriptorSetLayout>(6);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_CreatePipelineLayout(VkDevice,const VkPipelineLayoutCreateInfo *info,const VkAllocationCallbacks *,VkPipelineLayout *out){assert(info->pushConstantRangeCount==1&&(info->pPushConstantRanges[0].size==8||info->pPushConstantRanges[0].size==16));*out=handle<VkPipelineLayout>(7);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_CreateShaderModule(VkDevice,const VkShaderModuleCreateInfo *info,const VkAllocationCallbacks *,VkShaderModule *out){assert(info->codeSize==20);*out=handle<VkShaderModule>(8);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_CreateComputePipelines(VkDevice,VkPipelineCache cache,std::uint32_t n,const VkComputePipelineCreateInfo *,const VkAllocationCallbacks *,VkPipeline *out){assert(!cache&&n==1);*out=handle<VkPipeline>(100+(++pipelines));return VK_SUCCESS;}
VkResult VKAPI_CALL fake_CreateDescriptorPool(VkDevice,const VkDescriptorPoolCreateInfo *,const VkAllocationCallbacks *,VkDescriptorPool *out){*out=handle<VkDescriptorPool>(9);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_AllocateDescriptorSets(VkDevice,const VkDescriptorSetAllocateInfo *,VkDescriptorSet *out){*out=handle<VkDescriptorSet>(10);return VK_SUCCESS;}
void VKAPI_CALL fake_UpdateDescriptorSets(VkDevice,std::uint32_t n,const VkWriteDescriptorSet *writes,std::uint32_t,const VkCopyDescriptorSet *){assert(n==2&&writes[0].dstBinding==0&&writes[1].dstBinding==1);}
VkResult VKAPI_CALL fake_CreateCommandPool(VkDevice,const VkCommandPoolCreateInfo *,const VkAllocationCallbacks *,VkCommandPool *out){*out=handle<VkCommandPool>(11);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_AllocateCommandBuffers(VkDevice,const VkCommandBufferAllocateInfo *,VkCommandBuffer *out){*out=handle<VkCommandBuffer>(12);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_CreateFence(VkDevice,const VkFenceCreateInfo *,const VkAllocationCallbacks *,VkFence *out){*out=handle<VkFence>(13);return VK_SUCCESS;}
VkResult VKAPI_CALL fake_ResetFences(VkDevice,std::uint32_t n,const VkFence *){assert(n==1);++resets;return VK_SUCCESS;}
VkResult VKAPI_CALL fake_ResetCommandBuffer(VkCommandBuffer,VkCommandBufferResetFlags){return VK_SUCCESS;}
VkResult VKAPI_CALL fake_BeginCommandBuffer(VkCommandBuffer,const VkCommandBufferBeginInfo *){return VK_SUCCESS;}
void VKAPI_CALL fake_CmdPipelineBarrier(VkCommandBuffer,VkPipelineStageFlags src,VkPipelineStageFlags dst,VkDependencyFlags,std::uint32_t n,const VkMemoryBarrier *b,std::uint32_t,const VkBufferMemoryBarrier *,std::uint32_t,const VkImageMemoryBarrier *){
    assert(n==1);
    if(barriers%2==0)assert(src==VK_PIPELINE_STAGE_HOST_BIT&&dst==VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT&&b->srcAccessMask==VK_ACCESS_HOST_WRITE_BIT);
    else assert(src==VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT&&dst==VK_PIPELINE_STAGE_HOST_BIT&&b->dstAccessMask==VK_ACCESS_HOST_READ_BIT);
    ++barriers;
}
void VKAPI_CALL fake_CmdBindPipeline(VkCommandBuffer,VkPipelineBindPoint,VkPipeline pipeline){bound=pipeline;}
void VKAPI_CALL fake_CmdBindDescriptorSets(VkCommandBuffer,VkPipelineBindPoint,VkPipelineLayout,std::uint32_t,std::uint32_t,const VkDescriptorSet *,std::uint32_t,const std::uint32_t *){}
void VKAPI_CALL fake_CmdPushConstants(VkCommandBuffer,VkPipelineLayout,VkShaderStageFlags,std::uint32_t offset,std::uint32_t size,const void *data){assert(offset==0&&(size==8||size==16));std::memcpy(constants.data(),data,size);}
void VKAPI_CALL fake_CmdDispatch(VkCommandBuffer,std::uint32_t x,std::uint32_t y,std::uint32_t z){
    assert(y==1&&z==1);++dispatches;
    if(bound==handle<VkPipeline>(103)||bound==handle<VkPipeline>(104)) {
        assert(x==constants[1]);const unsigned columns=constants[0],rows=constants[1];
        std::vector<unsigned char> restored(columns*rows*2);const unsigned char *weights=source_bytes;
        if(bound==handle<VkPipeline>(104)){assert(qwen_palette_decode(source_bytes,constants[3],restored.data(),restored.size()));weights=restored.data();}
        for(unsigned row=0;row<rows;++row){float result=0;
            for(unsigned col=0;col<columns;++col){const auto i=std::size_t(row)*columns+col;
                std::uint32_t bits=(std::uint32_t(weights[2*i])|(std::uint32_t(weights[2*i+1])<<8))<<16;float value;std::memcpy(&value,&bits,4);
                result+=value*(float(int(col%7)-3)*0.5f);}
            std::memcpy(target_bytes+4*row,&result,4);
        }
        return;
    }
    assert(x==(constants[0]/2+255)/256);
    // The host substitutes execution only to test API sequencing and ownership.
    // This is not execution or qualification of the SPIRV kernel.
    if(bound==handle<VkPipeline>(101))std::memcpy(target_bytes,source_bytes,constants[0]*2);
    else assert(qwen_palette_decode(source_bytes,constants[1],target_bytes,constants[0]*2));
}
VkResult VKAPI_CALL fake_EndCommandBuffer(VkCommandBuffer){return VK_SUCCESS;}
VkResult VKAPI_CALL fake_QueueSubmit(VkQueue,std::uint32_t n,const VkSubmitInfo *,VkFence){assert(n==1);++submits;return fail_submit?VK_ERROR_DEVICE_LOST:VK_SUCCESS;}
VkResult VKAPI_CALL fake_WaitForFences(VkDevice,std::uint32_t n,const VkFence *,VkBool32 all,std::uint64_t timeout){assert(n==1&&all==VK_TRUE&&timeout==2000000000ull);++waits;return timeout_wait?VK_TIMEOUT:VK_SUCCESS;}
PFN_vkVoidFunction resolve(const char *name) {
#define MATCH(api) if(std::strcmp(name,"vk" #api)==0){static_assert(std::is_same_v<decltype(&fake_##api),PFN_vk##api>);return reinterpret_cast<PFN_vkVoidFunction>(&fake_##api);}
    MATCH(CreateInstance) MATCH(EnumeratePhysicalDevices) MATCH(GetPhysicalDeviceQueueFamilyProperties)
    MATCH(CreateDevice) MATCH(GetDeviceQueue) MATCH(GetPhysicalDeviceMemoryProperties)
    MATCH(CreateBuffer) MATCH(GetBufferMemoryRequirements) MATCH(AllocateMemory) MATCH(BindBufferMemory) MATCH(MapMemory)
    MATCH(CreateDescriptorSetLayout) MATCH(CreatePipelineLayout) MATCH(CreateShaderModule) MATCH(CreateComputePipelines)
    MATCH(CreateDescriptorPool) MATCH(AllocateDescriptorSets) MATCH(UpdateDescriptorSets) MATCH(CreateCommandPool)
    MATCH(AllocateCommandBuffers) MATCH(CreateFence) MATCH(ResetFences) MATCH(ResetCommandBuffer) MATCH(BeginCommandBuffer)
    MATCH(CmdPipelineBarrier) MATCH(CmdBindPipeline) MATCH(CmdBindDescriptorSets) MATCH(CmdPushConstants) MATCH(CmdDispatch)
    MATCH(EndCommandBuffer) MATCH(QueueSubmit) MATCH(WaitForFences)
#undef MATCH
    return nullptr;
}
template<class F>void rejected(F action){bool failed=false;try{action();}catch(const Halt &){failed=true;}assert(failed);}
}
extern "C" PFN_vkVoidFunction vkGetInstanceProcAddr(VkInstance,const char *name){return resolve(name);}
extern "C" PFN_vkVoidFunction vkGetDeviceProcAddr(VkDevice,const char *name){return resolve(name);}
extern "C" void qwen_native_stage(const char *){}
extern "C" [[noreturn]]void qwen_native_halt(const char *reason){throw Halt(reason);}
int main() {
    const std::array<std::uint32_t,5> spv{0x07230203,0,0,0,0};
    reset();auto *gpu=new PaletteGpuDispatch(spv.data(),20,spv.data(),20);
    std::vector<unsigned char> raw(131072),encoded(qwen_palette_bound(65536));
    for(unsigned i=0;i<65536;++i){raw[2*i]=static_cast<unsigned char>(i);raw[2*i+1]=static_cast<unsigned char>(i>>8);}
    const auto bytes=qwen_palette_encode(raw.data(),raw.size(),encoded.data(),encoded.size());assert(bytes);
    std::memcpy(gpu->source(),raw.data(),raw.size());gpu->dispatch(false,65536,131072);
    assert(std::memcmp(gpu->target(),raw.data(),raw.size())==0&&creates==1&&allocations==2&&submits==1&&waits==1&&barriers==2);
    std::memcpy(gpu->source(),encoded.data(),bytes);gpu->dispatch(true,65536,static_cast<std::uint32_t>(bytes));
    assert(std::memcmp(gpu->target(),raw.data(),raw.size())==0&&submits==2&&waits==2&&barriers==4);
    const auto before=resets;rejected([&]{gpu->dispatch(false,0,1);});assert(resets==before);
    timeout_wait=true;rejected([&]{gpu->dispatch(false,65536,131072);});
    const auto old_resets=resets,old_submits=submits;
    rejected([&]{gpu->dispatch(false,65536,131072);});assert(resets==old_resets&&submits==old_submits);
    reset();coherent=false;rejected([&]{new PaletteGpuDispatch(spv.data(),20,spv.data(),20);});assert(allocations==0);
    reset();oversized=true;rejected([&]{new PaletteGpuDispatch(spv.data(),20,spv.data(),20);});assert(allocations==0);
    reset();gpu=new PaletteGpuDispatch(spv.data(),20,spv.data(),20);fail_submit=true;
    rejected([&]{gpu->dispatch(false,65536,131072);});assert(waits==0);
    const auto failed_resets=resets;rejected([&]{gpu->dispatch(false,65536,131072);});assert(resets==failed_resets);
    reset();rejected([&]{new PaletteGpuDispatch(spv.data(),19,spv.data(),20);});assert(creates==0);
    reset();gpu=new PaletteGpuDispatch(spv.data(),20,spv.data(),20,spv.data(),20,spv.data(),20);
    assert(pipelines==4&&allocations==2);
    std::vector<unsigned char> matrix(3276800),packed(qwen_palette_bound(1638400));
    for(std::size_t i=0;i<matrix.size();i+=2){matrix[i]=0x80;matrix[i+1]=0x3f;}
    std::memcpy(gpu->source(),matrix.data(),matrix.size());gpu->matvec(false,2560,640,3276800);
    std::vector<unsigned char> expected(gpu->target(),gpu->target()+640*4);
    auto packed_bytes=qwen_palette_encode(matrix.data(),matrix.size(),packed.data(),packed.size());assert(packed_bytes);
    std::memcpy(gpu->source(),packed.data(),packed_bytes);gpu->matvec(true,2560,640,static_cast<std::uint32_t>(packed_bytes));
    assert(std::memcmp(gpu->target(),expected.data(),expected.size())==0&&submits==2&&waits==2&&dispatches==2&&barriers==4);
    std::memcpy(gpu->source(),matrix.data(),matrix.size());gpu->matvec(false,640,2560,3276800);
    expected.assign(gpu->target(),gpu->target()+2560*4);
    std::memcpy(gpu->source(),packed.data(),packed_bytes);gpu->matvec(true,640,2560,static_cast<std::uint32_t>(packed_bytes));
    assert(std::memcmp(gpu->target(),expected.data(),expected.size())==0&&submits==4&&waits==4&&dispatches==4&&barriers==8);
    const auto before_bad=resets;rejected([&]{gpu->matvec(false,2560,640,1);});rejected([&]{gpu->matvec(false,2560,641,3276800);});assert(resets==before_bad);
    timeout_wait=true;rejected([&]{gpu->matvec(false,2560,640,3276800);});const auto failed_matvec_resets=resets;
    rejected([&]{gpu->matvec(false,2560,640,3276800);});rejected([&]{gpu->dispatch(false,65536,131072);});assert(resets==failed_matvec_resets);
    reset();rejected([&]{new PaletteGpuDispatch(spv.data(),20,spv.data(),20,spv.data(),20);});assert(creates==0);
    return 0;
}
