// SPDX-License-Identifier: MIT
#include "virtual_source.h"
#include <ps5platform/kernel.h>
#include <string>
extern "C" void qwen_native_stage(const char *);
namespace qwen_app {
namespace {
class NativeVirtualOps final : public VirtualSourceOps {
public:
    std::uintptr_t reserve(std::size_t bytes) override {
        const auto stage="source_virtual_reserve_before_native_call bytes="+std::to_string(bytes)+" file_mmap_calls=0";
        qwen_native_stage(stage.c_str());void * address=nullptr;
        const auto rc=sceKernelReserveVirtualRange(&address,bytes,0,16384);
        qwen_native_stage("source_virtual_reserve_native_call_returned file_mmap_calls=0");
        if (rc) throw std::runtime_error("Native source virtual reservation rejected, code="+std::to_string(rc));
        return reinterpret_cast<std::uintptr_t>(address);
    }
    bool protection(std::uintptr_t at,std::uintptr_t & first,std::uintptr_t & last,std::uint32_t & bits) override {
        void * a=nullptr,*b=nullptr;
        qwen_native_stage("source_virtual_protection_before_native_call file_mmap_calls=0");
        const auto rc=sceKernelQueryMemoryProtection(reinterpret_cast<void *>(at),&a,&b,&bits);
        qwen_native_stage("source_virtual_protection_native_call_returned file_mmap_calls=0");
        first=reinterpret_cast<std::uintptr_t>(a);last=reinterpret_cast<std::uintptr_t>(b);return rc==0;
    }
    bool release(std::uintptr_t at,std::size_t bytes) override {
        qwen_native_stage("source_virtual_release_before_native_call file_mmap_calls=0");
        const auto rc=sceKernelMunmap(reinterpret_cast<void *>(at),bytes);
        qwen_native_stage("source_virtual_release_native_call_returned file_mmap_calls=0");return rc==0;
    }
};
}
std::uintptr_t reserve_native_virtual_source(std::uint64_t bytes) {
    NativeVirtualOps ops;return reserve_virtual_source(bytes,ops);
}
void release_native_virtual_source(std::uintptr_t at,std::uint64_t bytes) {
    NativeVirtualOps ops;release_virtual_source(at,bytes,ops);
}
}
extern "C" void * qwen_app_model_source_reserve_virtual(std::size_t bytes) {
    return reinterpret_cast<void *>(qwen_app::reserve_native_virtual_source(bytes));
}
extern "C" int qwen_app_model_source_release_virtual(void * at,std::size_t bytes) {
    qwen_app::release_native_virtual_source(reinterpret_cast<std::uintptr_t>(at),bytes);return 0;
}
