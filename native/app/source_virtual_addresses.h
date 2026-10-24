// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// CPU source keys occupy a separate interval above the pinned native driver's
// complete [256,512) GiB interval and the [128,144) GiB Direct heap. These are
// no-access reservations, never physical capacity or GPU buffer addresses.
inline constexpr std::uintptr_t source_key_base=512ull<<30;
inline constexpr std::size_t source_key_bytes=384ull<<30;
class SourceVirtualAddresses {
    struct Span {std::uintptr_t at=0;std::size_t bytes=0;};
    std::array<Span,80> live_{};
    std::size_t count_=0;
    bool healthy_=true;
    void ready() const {
        if(!healthy_)throw std::runtime_error("Source virtual address state retained after a failed native operation");
    }
public:
    void retain() noexcept {healthy_=false;}
    std::uintptr_t claim(std::size_t bytes) {
        ready();
        if(!bytes || bytes%16384 || bytes>source_key_bytes || count_==live_.size())
            throw std::runtime_error("Source virtual address capacity rejected before native reservation");
        auto at=source_key_base;std::size_t index=0;
        for(;index<count_;++index) {
            if(bytes<=live_[index].at-at)break;
            at=live_[index].at+live_[index].bytes;
        }
        if(at<source_key_base || at-source_key_base>source_key_bytes ||
           bytes>source_key_bytes-(at-source_key_base))
            throw std::runtime_error("Disjoint source virtual address interval exhausted");
        for(auto i=count_;i>index;--i)live_[i]=live_[i-1];
        live_[index]={at,bytes};++count_;return at;
    }
    std::size_t owned(std::uintptr_t at) const {
        ready();
        for(std::size_t i=0;i<count_;++i)if(live_[i].at==at)return live_[i].bytes;
        throw std::runtime_error("Source virtual address is not owned");
    }
    void retire(std::uintptr_t at,std::size_t bytes) {
        if(owned(at)!=bytes)throw std::runtime_error("Source virtual release span does not match its owner");
        std::size_t i=0;while(live_[i].at!=at)++i;
        for(;i+1<count_;++i)live_[i]=live_[i+1];
        live_[--count_]={};
    }
};
static_assert(source_key_base==(1ull<<39) && source_key_base+source_key_bytes==(896ull<<30));
}
