// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace qwen_app {
// A single inference-owner ring. Sampling never admits work, waits, allocates,
// writes files, changes a reserve, or requests reclamation. Preserve the last
// boundaries even when a later sample fails. Display/compiler workers must not
// call this object.
struct BoundaryMemorySample {
    char phase[64]{};
    std::uint64_t sequence=0,monotonic_ns=0,flexible_bytes=0,heap_mapped=0,heap_peak=0;
    std::uint32_t kernel_free=0;
    bool valid=false;
};
class BoundaryMemoryTrace {
public:
    static constexpr std::size_t capacity=64;
    template<class Observer> void record(const char *phase,Observer observe) noexcept {
        if(!phase||!phase[0]||std::strlen(phase)>=sizeof(BoundaryMemorySample::phase)) {
            invalid_=true;return;
        }
        BoundaryMemorySample sample{};
        std::memcpy(sample.phase,phase,std::strlen(phase)+1);
        sample.sequence=++sequence_;
        try { observe(sample); }
        catch(...) { sample.valid=false; }
        if(!sample.valid)invalid_=true;
        samples_[(sequence_-1)%capacity]=sample;
    }
    std::size_t size() const {return sequence_<capacity?std::size_t(sequence_):capacity;}
    std::uint64_t total() const {return sequence_;}
    bool invalid() const {return invalid_;}
    const BoundaryMemorySample &at(std::size_t ordinal) const {
        return samples_[(sequence_-size()+ordinal)%capacity];
    }
private:
    std::array<BoundaryMemorySample,capacity> samples_{};
    std::uint64_t sequence_=0;
    bool invalid_=false;
};
}
