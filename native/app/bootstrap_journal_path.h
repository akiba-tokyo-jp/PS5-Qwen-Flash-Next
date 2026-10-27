// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
namespace qwen_app {
// No allocator, formatted I/O or C++ constructor is needed before preinit.
inline bool bootstrap_journal_path(char *output,std::size_t capacity,
        std::int64_t boot_seconds,std::int64_t boot_microseconds,int pid,const char *suffix) {
    if(!output||!suffix||boot_seconds<=0||boot_microseconds<0||boot_microseconds>=1000000||pid<=0||
       (std::strcmp(suffix,".stages")&&std::strcmp(suffix,".fatal")&&std::strcmp(suffix,".private.log")))return false;
    const char *prefix="/app0/qwen-runtime/entry-b";const auto length=std::strlen(prefix);
    if(capacity<=length)return false;std::memcpy(output,prefix,length);std::size_t used=length;
    const auto decimal=[&](std::uint64_t value){char reversed[20];unsigned n=0;
        do {reversed[n++]=char('0'+value%10);value/=10;}while(value);
        if(n>=capacity-used)return false;while(n)output[used++]=reversed[--n];return true;};
    if(!decimal(static_cast<std::uint64_t>(boot_seconds)))return false;
    if(used+1>=capacity)return false;output[used++]='-';
    if(!decimal(static_cast<std::uint64_t>(boot_microseconds)))return false;
    if(used+1>=capacity)return false;output[used++]='-';
    if(!decimal(static_cast<unsigned>(pid)))return false;
    const auto suffix_length=std::strlen(suffix);if(suffix_length>=capacity-used)return false;
    std::memcpy(output+used,suffix,suffix_length+1);return true;
}
}
