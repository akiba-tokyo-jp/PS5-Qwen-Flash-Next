// SPDX-License-Identifier: MIT
#include "virtual_source.h"
#include "source_virtual_addresses.h"
#include <ps5platform/kernel.h>
#include <mutex>
#include <string>
extern "C" void qwen_native_stage(const char *);
namespace qwen_app {
namespace {
struct AddressBook {std::mutex mutex;qwen_app::SourceVirtualAddresses addresses;};
AddressBook & address_book() {static AddressBook book;return book;}
class NativeVirtualOps final : public VirtualSourceOps {
public:
    std::uintptr_t reserve(std::size_t bytes) override {
        const auto stage="source_virtual_reserve_before_native_call bytes="+std::to_string(bytes)+" file_mmap_calls=0";
        auto & book=address_book();std::lock_guard<std::mutex> guard(book.mutex);
        const auto expected=book.addresses.claim(bytes);
        qwen_native_stage(stage.c_str());void * address=reinterpret_cast<void *>(expected);
        // Fixed plus no-overwrite: an occupied interval must be rejected. Never
        // replace a mapping, search again after rejection or rely on a hint.
        const auto rc=sceKernelReserveVirtualRange(&address,bytes,0x10|0x80,16384);
        qwen_native_stage("source_virtual_reserve_native_call_returned file_mmap_calls=0");
        const auto result="source_virtual_reserve_result rc="+std::to_string(rc)+
            " address="+std::to_string(reinterpret_cast<std::uintptr_t>(address))+" bytes="+std::to_string(bytes);
        qwen_native_stage(result.c_str());
        if(rc || reinterpret_cast<std::uintptr_t>(address)!=expected) {
            book.addresses.retain();
            throw std::runtime_error("Native source virtual reservation rejected, code="+std::to_string(rc));
        }
        return reinterpret_cast<std::uintptr_t>(address);
    }
    bool protection(std::uintptr_t at,std::uintptr_t & first,std::uintptr_t & last,std::uint32_t & bits) override {
        auto & book=address_book();std::lock_guard<std::mutex> guard(book.mutex);
        const auto bytes=book.addresses.owned(at);
        void * a=nullptr,*b=nullptr;
        qwen_native_stage("source_virtual_protection_before_native_call file_mmap_calls=0");
        const auto rc=sceKernelQueryMemoryProtection(reinterpret_cast<void *>(at),&a,&b,&bits);
        qwen_native_stage("source_virtual_protection_native_call_returned file_mmap_calls=0");
        first=reinterpret_cast<std::uintptr_t>(a);last=reinterpret_cast<std::uintptr_t>(b);
        const bool completed=rc==0 && first<=at && last>=at+bytes && !bits;
        if(!completed)book.addresses.retain();
        return completed;
    }
    bool release(std::uintptr_t at,std::size_t bytes) override {
        auto & book=address_book();std::lock_guard<std::mutex> guard(book.mutex);
        if(book.addresses.owned(at)!=bytes)throw std::runtime_error("Unowned source virtual release rejected before native call");
        qwen_native_stage("source_virtual_release_before_native_call file_mmap_calls=0");
        const auto rc=sceKernelMunmap(reinterpret_cast<void *>(at),bytes);
        qwen_native_stage("source_virtual_release_native_call_returned file_mmap_calls=0");
        if(rc)book.addresses.retain();else book.addresses.retire(at,bytes);
        return rc==0;
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
