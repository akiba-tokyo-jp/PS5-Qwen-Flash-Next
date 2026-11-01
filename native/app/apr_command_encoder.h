// SPDX-License-Identifier: GPL-3.0-or-later
// Derived from drakmor/ampr_emu cfa85df379f6eeeb165d7badf9b648e266fe77b7,
// src/ampr_emu_command_packing.cpp. No emulator runtime or system binary.
#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace qwen_app {
struct AprCommandBuffer {
    std::int32_t type=0;
    std::uint32_t offset=0;
    volatile std::int32_t commands=0;
    std::uint32_t capacity=0;
    void* storage=nullptr;
    std::uint64_t map_state=0,scatter_state=0;
};
static_assert(sizeof(AprCommandBuffer)==40&&offsetof(AprCommandBuffer,storage)==16&&offsetof(AprCommandBuffer,map_state)==24,"Public APR ABI");
inline bool apr_bind(AprCommandBuffer&cb,void*storage,std::uint32_t capacity){
    if(!storage||(reinterpret_cast<std::uintptr_t>(storage)&3)||!capacity||(capacity&3)||capacity>(64u<<20))return false;
    cb.type=0;cb.offset=0;cb.commands=0;cb.capacity=capacity;cb.storage=storage;cb.map_state=cb.scatter_state=0;return true;
}
inline bool apr_append(AprCommandBuffer&cb,const std::uint32_t*words,unsigned count){
    const auto bytes=count*4u;
    if(!cb.storage||cb.offset>cb.capacity||bytes>cb.capacity-cb.offset||cb.commands<0||cb.commands==INT32_MAX)return false;
    std::memcpy(static_cast<unsigned char*>(cb.storage)+cb.offset,words,bytes);cb.offset+=bytes;++cb.commands;return true;
}
inline bool apr_read(AprCommandBuffer&cb,std::uint32_t file,void*target,std::uint64_t bytes,std::uint64_t offset){
    const auto address=reinterpret_cast<std::uintptr_t>(target);
    if(file==UINT32_MAX||!address||address>=(UINT64_C(1)<<48)||!bytes||bytes>(UINT64_C(1)<<32)||
       bytes>(UINT64_C(1)<<48)-address||offset>=(UINT64_C(1)<<40))return false;
    const unsigned count=(offset>>32)?6u:5u;
    std::uint32_t w[6]={((std::uint32_t(offset)<<12)&0x3ffff000u)|(((count<<8)+1792u)&0x700u)|40u,
        std::uint32_t(bytes-1),file&0x7fffffffu,std::uint32_t(address),
        std::uint32_t((address>>32)&0xffffu)|(std::uint32_t(offset)&0xfffc0000u),std::uint32_t((offset>>32)&0xffu)};
    return apr_append(cb,w,count);
}
inline bool apr_completion(AprCommandBuffer&cb,volatile std::uint64_t*target,std::uint64_t value){
    const auto address=reinterpret_cast<std::uintptr_t>(target);
    if(!address||(address&7)||address>=(UINT64_C(1)<<48))return false;
    const unsigned count=value<4?2u:value<UINT64_C(0x400000000)?3u:4u;
    std::uint32_t w[4]={std::uint32_t((address>>16)&0xffff0000u)|(((count<<8)+3840u)&0xf00u)|5u|
        (std::uint32_t(value&3)<<12)|std::uint16_t((count<<14)+0x8000u),
        std::uint32_t(address&0xfffffff8u),std::uint32_t(value>>2),std::uint32_t(value>>34)};
    return apr_append(cb,w,count);
}
}
