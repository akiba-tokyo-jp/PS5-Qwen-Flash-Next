// SPDX-License-Identifier: MIT
#include "owned_mapped_probe.h"
#include "padded_bank_bridge.h"
#include "padded_bank.h"
#include "padded_cache_geometry.h"
#include "split_bank_bridge.h"
#include "ggml-backend-impl.h"
#include "ggml-vulkan-common.h"
#include <type_traits>

namespace {
template<class Handle> std::uint64_t split_allocation_identity(Handle handle) {
    if constexpr(std::is_pointer_v<Handle>)return std::uint64_t(reinterpret_cast<std::uintptr_t>(handle));
    else return std::uint64_t(handle);
}
}
extern "C" int ggml_app_vk_probe_owned_matvec(ggml_tensor *tensor,
    int (*writer)(void *,size_t,uint64_t,void *),void *opaque) {
    if(!tensor||!writer||tensor->view_src||tensor->view_offs||!tensor->buffer||
       !ggml_backend_buffer_is_vk(tensor->buffer)||tensor->type!=GGML_TYPE_BF16||
       tensor->ne[0]!=2560||tensor->ne[1]!=640||tensor->ne[2]!=1||tensor->ne[3]!=1||
       !ggml_is_contiguous(tensor)||ggml_nbytes(tensor)!=3276800)
        throw std::invalid_argument("Owned mapped probe tensor refused");
    auto *owner=static_cast<ggml_backend_vk_buffer_context *>(tensor->buffer->context);
    const auto lease=owner->dev_buffer;
    const auto required=vk::MemoryPropertyFlagBits::eDeviceLocal|
        vk::MemoryPropertyFlagBits::eHostVisible|vk::MemoryPropertyFlagBits::eHostCoherent;
    if(!lease||!lease->ptr||(lease->memory_property_flags&required)!=required)return 1;
    const size_t offset=vk_tensor_offset(tensor);
    if(offset>lease->size||3276800>lease->size-offset||
       reinterpret_cast<uintptr_t>(lease->ptr)>UINTPTR_MAX-offset)
        throw std::length_error("Owned mapped probe allocation extent refused");
    auto *destination=static_cast<uint8_t *>(lease->ptr)+offset;
    if(reinterpret_cast<uintptr_t>(destination)%16384)return 1;
    const int result=writer(destination,3276800,static_cast<uint32_t>(lease->memory_property_flags),opaque);
    if(tensor->buffer->context!=owner||owner->dev_buffer!=lease||(result!=0&&result!=1))
        throw std::runtime_error("Owned mapped probe lease changed; backing retained");
    return result;
}

extern "C" int ggml_app_vk_probe_owned_bank(ggml_tensor *tensor,
    int (*writer)(void *,size_t,uint64_t,size_t,void *),void *opaque) {
    const auto geometry=qwen_app::selected_padded_cache_geometry();
    if(!tensor||!writer||tensor->view_src||tensor->view_offs||!tensor->buffer||
       !ggml_backend_buffer_is_vk(tensor->buffer)||tensor->type!=GGML_TYPE_BF16||
       !((tensor->ne[0]==2560&&tensor->ne[1]==640)||(tensor->ne[0]==640&&tensor->ne[1]==2560))||
       tensor->ne[2]!=static_cast<std::int64_t>(geometry.physical_slots())||tensor->ne[3]!=1||
       tensor->nb[0]!=2||tensor->nb[1]!=std::size_t(tensor->ne[0])*2||
       tensor->nb[2]!=qwen_app::padded_bank_stride||
       ggml_nbytes(tensor)!=geometry.tensor_bytes())
        throw std::invalid_argument("Owned padded-bank root tensor refused");
    auto *owner=static_cast<ggml_backend_vk_buffer_context *>(tensor->buffer->context);
    const auto lease=owner->dev_buffer;
    const auto required=vk::MemoryPropertyFlagBits::eDeviceLocal|
        vk::MemoryPropertyFlagBits::eHostVisible|vk::MemoryPropertyFlagBits::eHostCoherent;
    if(!lease||!lease->ptr||(lease->memory_property_flags&required)!=required)return 1;
    const size_t offset=vk_tensor_offset(tensor);
    if(offset>lease->size||geometry.tensor_bytes()>lease->size-offset||
       reinterpret_cast<uintptr_t>(lease->ptr)>UINTPTR_MAX-offset)
        throw std::length_error("Owned padded-bank allocation extent refused");
    auto *destination=static_cast<uint8_t *>(lease->ptr)+offset;
    if(reinterpret_cast<uintptr_t>(destination)%qwen_app::bank_read_alignment)return 1;
    const auto alignment=lease->device->properties.limits.minStorageBufferOffsetAlignment;
    const int result=writer(destination,geometry.tensor_bytes(),
        static_cast<uint32_t>(lease->memory_property_flags),alignment,opaque);
    if(tensor->buffer->context!=owner||owner->dev_buffer!=lease||(result!=0&&result!=1))
        throw std::runtime_error("Padded-bank lease changed; backing retained");
    return result;
}

extern "C" int ggml_app_vk_probe_owned_split_bank(ggml_tensor *tensor,unsigned group,
    int (*writer)(const qwen_app::SplitBankLease &,void *),void *opaque) {
    if(!writer||!qwen_app::split_bank_root_layout(tensor,group)||!tensor->buffer||
       !ggml_backend_buffer_is_vk(tensor->buffer))
        throw std::invalid_argument("Experimental split bank requires its exact byte-storage root");
    auto *owner=static_cast<ggml_backend_vk_buffer_context *>(tensor->buffer->context);
    if(!owner)throw std::invalid_argument("Experimental split bank has no actual buffer owner");
    const auto lease=owner->dev_buffer;
    const auto required=vk::MemoryPropertyFlagBits::eDeviceLocal|
        vk::MemoryPropertyFlagBits::eHostVisible|vk::MemoryPropertyFlagBits::eHostCoherent;
    if(!lease||!lease->ptr||(lease->memory_property_flags&required)!=required)return 1;
    const auto allocation=split_allocation_identity(static_cast<VkDeviceMemory>(lease->device_memory));
    if(!allocation||!lease->device)return 1;
    const std::size_t offset=vk_tensor_offset(tensor),bytes=ggml_nbytes(tensor);
    if(offset>lease->size||bytes>lease->size-offset||
       reinterpret_cast<std::uintptr_t>(lease->ptr)>UINTPTR_MAX-offset)
        throw std::length_error("Experimental split-bank allocation extent refused");
    auto *destination=static_cast<std::uint8_t *>(lease->ptr)+offset;
    if(reinterpret_cast<std::uintptr_t>(destination)%qwen_app::bank_read_alignment)return 1;
    const auto alignment=lease->device->properties.limits.minStorageBufferOffsetAlignment;
    if(!alignment||alignment>qwen_app::bank_read_alignment||qwen_app::bank_read_alignment%alignment)return 1;
    const qwen_app::SplitBankLease grant{destination,bytes,alignment,
        static_cast<std::uint32_t>(lease->memory_property_flags),allocation};
    const int result=writer(grant,opaque);
    if(tensor->buffer->context!=owner||owner->dev_buffer!=lease||
       split_allocation_identity(static_cast<VkDeviceMemory>(lease->device_memory))!=allocation||
       (result!=0&&result!=1))
        throw std::runtime_error("Experimental split-bank lease changed; backing must be retained");
    return result;
}
