// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
// Diagnostic only. Individual call wall times overlap on the two I/O lanes;
// their sum must never be added to the enclosing producer wait interval.
class SourceReadLatency {
public:
    static constexpr std::size_t bins=65,size_bins=17,fields=4+bins+3*size_bins;
    static constexpr std::uint64_t bin_ns=128000;
    static constexpr std::uint64_t size_bin_bytes=65536;
    using Snapshot=std::array<std::uint64_t,fields>;
private:
    std::array<std::atomic<std::uint64_t>,fields> counters_{};
public:
    void completed(std::int64_t got,std::uint64_t ns) noexcept {
        counters_[0].fetch_add(1,std::memory_order_relaxed);
        if(got<0){counters_[3].fetch_add(1,std::memory_order_relaxed);return;}
        counters_[1].fetch_add(std::uint64_t(got),std::memory_order_relaxed);
        counters_[2].fetch_add(ns,std::memory_order_relaxed);
        const auto index=ns/bin_ns;
        counters_[4+(index>=bins-1?bins-1:index)].fetch_add(1,std::memory_order_relaxed);
        const auto size_index=std::uint64_t(got)/size_bin_bytes;
        const auto base=4+bins+3*(size_index>=size_bins-1?size_bins-1:size_index);
        counters_[base].fetch_add(1,std::memory_order_relaxed);
        counters_[base+1].fetch_add(std::uint64_t(got),std::memory_order_relaxed);
        counters_[base+2].fetch_add(ns,std::memory_order_relaxed);
    }
    Snapshot snapshot() const noexcept {
        Snapshot out{};
        for(std::size_t i=0;i<fields;++i)out[i]=counters_[i].load(std::memory_order_relaxed);
        return out;
    }
};
}
extern "C" void qwen_app_source_read_latency(std::uint64_t*,std::size_t);
