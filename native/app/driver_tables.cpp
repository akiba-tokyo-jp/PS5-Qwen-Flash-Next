// SPDX-License-Identifier: MIT
#include "driver_table_restore.h"
#include "system_memory.h"
#include <ps5platform/heap.h>
#include <sys/mman.h>
#include <array>
#include <stdexcept>
namespace {
struct Slot {void *p=nullptr;std::size_t bytes=0;};
struct Scratch {std::array<Slot,8> slots{};std::size_t live=0;bool fault=false;};
voidpf allocate(voidpf opaque,uInt n,uInt bytes) {
    auto &s=*static_cast<Scratch *>(opaque);
    if(!n||!bytes||std::size_t(n)>(1u<<20)/bytes||std::size_t(n)*bytes>(1u<<20)-s.live){s.fault=true;return nullptr;}
    for(auto &slot:s.slots)if(!slot.p){
        slot.p=ps5_heap_calloc(n,bytes);slot.bytes=std::size_t(n)*bytes;
        if(!slot.p||!ps5_heap_owns(slot.p)){s.fault=true;return nullptr;}
        s.live+=slot.bytes;return slot.p;
    }
    s.fault=true;return nullptr;
}
void release(voidpf opaque,voidpf p) {
    auto &s=*static_cast<Scratch *>(opaque);
    for(auto &slot:s.slots)if(p&&slot.p==p&&ps5_heap_owns(p)){
        ps5_heap_free(p);s.live-=slot.bytes;slot={};return;
    }
    s.fault=true;
}
int protect(void *p,std::size_t n){return mprotect(p,n,PROT_READ);}
}
namespace qwen_app {
void restore_native_driver_tables() {
    if(!&qwen_driver_table_storage)return;
    static bool attempted=false;
    if(attempted)throw std::runtime_error("Driver table restoration cannot be repeated");
    attempted=true;
    const auto memory=admit_native_system_memory();
    const auto required=std::uint64_t(memory.kernel_minimum)+
        std::max<std::uint64_t>(memory.kernel_reserved,kernel_memory_margin/memory.page_size)+512;
    if(memory.kernel_free<required)throw KernelMemoryPressure();
    Scratch scratch;
    if(!restore_driver_tables(qwen_driver_table_storage,allocate,release,&scratch,protect)||scratch.fault||scratch.live)
        throw std::runtime_error("Lossless driver tables failed exact restoration or readonly protection before Vulkan");
}
}
