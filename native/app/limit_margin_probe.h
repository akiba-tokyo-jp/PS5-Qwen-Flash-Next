// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <limits>
#include <stdexcept>

namespace qwen_app {
// Explicit experiment only. This changes application padding, never OS counters,
// physical allocation checks, source identity or positive GPU completion.
class LimitMarginProbe {
    struct Bucket {
        std::atomic<std::uint64_t> calls{0},legacy_refusals{0},reductions{0};
        std::atomic<std::uint64_t> minimum_free{UINT64_MAX},minimum_extra{UINT64_MAX};
    };
    std::array<Bucket,4> buckets_{};
    std::atomic<unsigned> phase_{0};
    std::atomic<std::uint64_t> current_{256};
    const bool stable_inference_;
    static void lower(std::atomic<std::uint64_t>&target,std::uint64_t value) {
        auto before=target.load(std::memory_order_relaxed);
        while(value<before&&!target.compare_exchange_weak(before,value,std::memory_order_relaxed)){}
    }
public:
    explicit LimitMarginProbe(bool stable_inference=false):stable_inference_(stable_inference){}
    void phase(unsigned phase) {
        const auto old=phase_.load(std::memory_order_relaxed);
        if(phase<1||phase>4||phase<old)throw std::logic_error("Ordered limit-probe phase required");
        if(stable_inference_&&phase>=3)current_.store(0,std::memory_order_relaxed);
        phase_.store(phase,std::memory_order_relaxed);
    }
    std::uint64_t required(std::uint64_t free,std::uint64_t minimum,std::uint64_t reserved,
                           std::uint64_t legacy_extra,std::uint64_t transient=0) {
        const auto phase=phase_.load(std::memory_order_relaxed);
        if(!phase)return minimum+legacy_extra+transient;
        if(!minimum||!reserved||reserved>minimum)throw std::invalid_argument("Observed OS thresholds required");
        auto&bucket=buckets_.at(phase-1);++bucket.calls;lower(bucket.minimum_free,free);
        if(free<minimum+legacy_extra+transient)++bucket.legacy_refusals;
        auto selected=stable_inference_&&phase<3?legacy_extra:std::min(legacy_extra,current_.load(std::memory_order_relaxed));
        if(stable_inference_){lower(bucket.minimum_extra,selected);return minimum+selected+transient;}
        while(free<minimum+selected+transient&&selected) {
            const auto next=selected>reserved?reserved:selected>128?128:selected>64?64:0;
            if(next>=selected)throw std::logic_error("Limit-probe padding must decrease");
            selected=next;lower(current_,selected);++bucket.reductions;
        }
        lower(bucket.minimum_extra,selected);
        // If free is below this result, the unchanged exception/wait path stops
        // before another operation. The probe cannot admit below the OS minimum.
        return minimum+selected+transient;
    }
    void snapshot(std::uint64_t*out)const {
        if(!out)throw std::invalid_argument("Limit-probe snapshot output required");
        out[0]=phase_.load();out[1]=current_.load();
        for(unsigned i=0;i<4;++i){const auto&b=buckets_[i];auto*p=out+2+5*i;
            p[0]=b.calls.load();p[1]=b.legacy_refusals.load();p[2]=b.reductions.load();
            p[3]=b.minimum_free.load();p[4]=b.minimum_extra.load();}
    }
};
}
