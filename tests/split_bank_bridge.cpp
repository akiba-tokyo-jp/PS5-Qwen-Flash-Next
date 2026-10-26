// SPDX-License-Identifier: MIT
#include "split_bank_bridge.h"
#include "ready_expert_wave.h"
#include <memory>
#include <iostream>
#include <cstdlib>
#include <type_traits>
namespace vk {
enum class MemoryPropertyFlagBits:std::uint32_t {eDeviceLocal=1,eHostVisible=2,eHostCoherent=4};
using MemoryPropertyFlags=std::uint32_t;
inline auto operator|(MemoryPropertyFlagBits a,MemoryPropertyFlagBits b){return std::uint32_t(a)|std::uint32_t(b);}
inline auto operator|(MemoryPropertyFlags a,MemoryPropertyFlagBits b){return a|std::uint32_t(b);}
}
using VkDeviceMemory=std::uint64_t;
struct MockDevice {struct {struct {std::size_t minStorageBufferOffsetAlignment=32;}limits;}properties;};
struct MockBuffer {void *ptr=nullptr;std::size_t size=0;vk::MemoryPropertyFlags memory_property_flags=7;
    VkDeviceMemory device_memory=71;std::shared_ptr<MockDevice>device=std::make_shared<MockDevice>();};
struct ggml_backend_vk_buffer_context {std::shared_ptr<MockBuffer>dev_buffer;std::size_t tensor_offset=0;};
struct ggml_backend_buffer {void *context=nullptr;bool native=true;};
static bool ggml_backend_buffer_is_vk(ggml_backend_buffer *b){return b&&b->native;}
static std::size_t vk_tensor_offset(ggml_tensor *t){return static_cast<ggml_backend_vk_buffer_context*>(t->buffer->context)->tensor_offset;}
#include "actual_owned_split.inc"
namespace {
void check(bool ok){if(!ok)throw std::runtime_error("Split-bank ownership check differs");}
unsigned calls=0;std::uint64_t observed_owner=0;
int writer(const qwen_app::SplitBankLease &g,void*){
    ++calls;check(g.destination&&g.bytes==27*qwen_app::padded_bank_stride&&g.descriptor_alignment==32&&g.memory_flags==7);
    observed_owner=g.allocation_owner;return 0;
}
}
int main(){
    auto *ctx=ggml_init({1u<<20,nullptr,true});check(ctx);
    auto *root=ggml_new_tensor_1d(ctx,GGML_TYPE_BF16,27*qwen_app::padded_bank_stride/2);
    auto buffer=std::make_shared<MockBuffer>();void *storage=std::malloc(32768);check(storage);
    void *allocation=reinterpret_cast<void *>((reinterpret_cast<std::uintptr_t>(storage)+16383)&~std::uintptr_t(16383));buffer->ptr=allocation;
    buffer->size=ggml_nbytes(root);ggml_backend_vk_buffer_context owner{buffer};ggml_backend_buffer backend{&owner,true};root->buffer=&backend;
    check(!ggml_app_vk_probe_owned_split_bank(root,0,writer,nullptr)&&calls==1&&observed_owner==71);
    check(!ggml_app_vk_probe_owned_split_bank(root,1,writer,nullptr)&&calls==2&&observed_owner==71);
    check(split_allocation_identity(allocation)==reinterpret_cast<std::uintptr_t>(allocation));
    unsigned refused=0;
    const auto reject=[&](auto edit,auto restore){const auto before=calls;edit();bool rejected=false;
        try{rejected=ggml_app_vk_probe_owned_split_bank(root,0,writer,nullptr)==1;}catch(const std::exception&){rejected=true;}
        restore();check(rejected&&calls==before);++refused;};
    reject([&]{root->type=GGML_TYPE_F16;},[&]{root->type=GGML_TYPE_BF16;});
    reject([&]{--root->ne[0];},[&]{++root->ne[0];});
    reject([&]{root->ne[1]=2;},[&]{root->ne[1]=1;});
    reject([&]{root->view_src=root;},[&]{root->view_src=nullptr;});
    reject([&]{root->view_offs=32;},[&]{root->view_offs=0;});
    reject([&]{backend.native=false;},[&]{backend.native=true;});
    reject([&]{backend.context=nullptr;},[&]{backend.context=&owner;});
    reject([&]{owner.dev_buffer.reset();},[&]{owner.dev_buffer=buffer;});
    reject([&]{buffer->ptr=nullptr;},[&]{buffer->ptr=allocation;});
    reject([&]{buffer->memory_property_flags=3;},[&]{buffer->memory_property_flags=7;});
    reject([&]{buffer->device_memory=0;},[&]{buffer->device_memory=71;});
    auto device=buffer->device;reject([&]{buffer->device.reset();},[&]{buffer->device=device;});
    reject([&]{buffer->size--;},[&]{buffer->size++;});
    reject([&]{owner.tensor_offset=16384;},[&]{owner.tensor_offset=0;});
    reject([&]{buffer->ptr=static_cast<unsigned char*>(allocation)+1;},[&]{buffer->ptr=allocation;});
    reject([&]{device->properties.limits.minStorageBufferOffsetAlignment=0;},[&]{device->properties.limits.minStorageBufferOffsetAlignment=32;});
    reject([&]{device->properties.limits.minStorageBufferOffsetAlignment=32768;},[&]{device->properties.limits.minStorageBufferOffsetAlignment=32;});
    try{ggml_app_vk_probe_owned_split_bank(root,2,writer,nullptr);check(false);}catch(const std::invalid_argument&){++refused;}
    try{ggml_app_vk_probe_owned_split_bank(root,0,nullptr,nullptr);check(false);}catch(const std::invalid_argument&){++refused;}
    bool changed=false;
    try{ggml_app_vk_probe_owned_split_bank(root,0,[](const auto&,void*p){auto *o=static_cast<ggml_backend_vk_buffer_context*>(p);o->dev_buffer=std::make_shared<MockBuffer>(*o->dev_buffer);return 0;},&owner);}
    catch(const std::runtime_error&){changed=true;}
    check(changed);owner.dev_buffer=buffer;
    // Different root objects still name the same physical allocation. This
    // must refuse overlap instead of treating distinct logical slots as safe.
    std::array<std::int32_t,10>ids{};std::array<unsigned,10>slots{};
    for(unsigned i=0;i<10;++i){ids[i]=i;slots[i]=i<5?i:26+i-5;}
    qwen_app::ReadyExpertWave::Owners shared{{{{71,71,71}},{{71,71,71}}}};
    qwen_app::ReadyExpertWave a(ids,slots,shared,23,1,1,1);check(!a.may_overlap_groups());
    auto distinct=shared;distinct[1]={{72,72,72}};
    qwen_app::ReadyExpertWave b(ids,slots,distinct,23,1,2,1);check(b.may_overlap_groups());
    root->buffer=nullptr;ggml_free(ctx);std::free(storage);
    std::cout<<"{\"root_and_lease_refusals\":"<<refused<<",\"changed_owner_refused\":true,\"same_allocation_overlap_refused\":true,\"API_mocks_only\":true,\"GPU_calls\":0}"<<std::endl;
}
