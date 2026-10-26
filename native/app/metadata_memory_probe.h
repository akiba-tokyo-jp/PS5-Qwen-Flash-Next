// SPDX-License-Identifier: MIT
#pragma once
#include "system_memory.h"
#include <array>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
// Fixed CPU-only observations retain the entire metadata interval, unlike the
// rolling inference trace. Recording never changes an allocation or OS floor.
class MetadataMemoryProbe {
public:
    static constexpr std::size_t files=76,phases=5,capacity=files*phases;
    struct Sample {
        SystemMemoryObservation memory;
        std::uint64_t monotonic_ns=0,heap_mapped=0,heap_peak=0;
        std::uint64_t direct_reads=0,direct_bytes=0;
    };
private:
    bool enabled_=false,failed_=false;
    std::size_t count_=0;
    std::array<Sample,capacity> records_{};
public:
    void enable() {
        if(enabled_||failed_||count_)throw std::runtime_error("Metadata probe may only be enabled once");
        enabled_=true;
    }
    bool enabled()const{return enabled_;}
    void record(std::size_t file,std::size_t phase,const Sample &s) {
        if(!enabled_||failed_)throw std::runtime_error("Metadata probe owner is inactive or failed");
        try {
            if(file>=files||phase>=phases||count_>=capacity||file*phases+phase!=count_||!s.monotonic_ns||
               !s.heap_mapped||s.heap_peak>s.heap_mapped||s.direct_reads>8192||s.direct_bytes>(512ull<<20))
                throw std::runtime_error("Metadata probe order or bounds differ");
            (void)qualified_system_headroom(s.memory);
            if(count_&&(s.monotonic_ns<records_[count_-1].monotonic_ns||
                s.direct_reads<records_[count_-1].direct_reads||s.direct_bytes<records_[count_-1].direct_bytes))
                throw std::runtime_error("Metadata probe counters moved backwards");
            records_[count_++]=s;
        }catch(...){failed_=true;throw;}
    }
    std::size_t size()const{return count_;}
    bool complete()const{return enabled_&&!failed_&&count_==capacity;}
    const Sample &at(std::size_t i)const {
        if(i>=count_)throw std::out_of_range("Metadata probe record is absent");
        return records_[i];
    }
};
static_assert(sizeof(MetadataMemoryProbe)<65536);
}
