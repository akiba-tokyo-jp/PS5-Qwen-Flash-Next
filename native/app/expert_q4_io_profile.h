// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <stdexcept>
#include <cstring>
namespace qwen_app {
// Producer-only, completed-counter observations. No reads, allocations, GPU
// operations or scheduling changes are performed by this diagnostic.
class ExpertQ4IOProfile {
public:
    struct Totals {std::uint64_t rows=0,logical=0,physical=0,calls=0,wait_ns=0;};
    std::array<Totals,3> totals{};
    bool enabled=false,live=false;
    unsigned kind=0;std::uint64_t expected=0,rows=0;
    struct Point {std::uint64_t bytes=0,physical_read_bytes=0,physical_read_calls=0,read_ns=0;}before;
    template<class Stats>void begin(const char*name,std::uint64_t count,std::uint64_t stride,const Stats&source){
        if(!enabled)return;
        if(live||!name||!count||!stride||count>UINT64_MAX/stride||source.chunks!=source.completed_windows)
            throw std::runtime_error("Completed non-overlapping CPU row attribution required");
        kind=!std::strcmp(name,"token_embd.weight")?0:!std::strcmp(name,"per_layer_token_embd.weight")?1:2;
        expected=count*stride;rows=count;
        before={source.bytes,source.physical_read_bytes,source.physical_read_calls,source.read_ns};live=true;
    }
    template<class Stats>void end(const Stats&source){
        if(!enabled)return;
        if(!live||source.chunks!=source.completed_windows||source.bytes<before.bytes||
            source.bytes-before.bytes!=expected||source.physical_read_bytes<before.physical_read_bytes||
            source.physical_read_calls<before.physical_read_calls||source.read_ns<before.read_ns)
            throw std::runtime_error("Complete exact CPU row reads required before attribution");
        auto&out=totals[kind];out.rows+=rows;out.logical+=expected;
        out.physical+=source.physical_read_bytes-before.physical_read_bytes;
        out.calls+=source.physical_read_calls-before.physical_read_calls;
        out.wait_ns+=source.read_ns-before.read_ns;live=false;
    }
};
}
