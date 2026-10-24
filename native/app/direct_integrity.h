// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <stdexcept>
#include <string>
namespace qwen_app {
inline constexpr std::size_t direct_integrity_alignment=16384;
inline constexpr std::size_t direct_integrity_window=1u<<20;
struct DirectIntegrityOps {
    virtual ~DirectIntegrityOps()=default;
    virtual std::int64_t read_at(void *,std::size_t,std::uint64_t)=0;
    virtual std::uint64_t now_ns()=0;
};
// Exact returned bytes are hashed, including a non-aligned EOF tail. A negative,
// short, oversized or timed-out result is never retried or published complete.
inline void stream_direct_integrity(DirectIntegrityOps & ops,void * buffer,std::uint64_t bytes,
        unsigned timeout_seconds,const std::function<void(const unsigned char *,std::size_t)> & consume) {
    if(!buffer||reinterpret_cast<std::uintptr_t>(buffer)%direct_integrity_alignment||!bytes||bytes>(512ull<<30)||
        !timeout_seconds||timeout_seconds>86400||!consume)throw std::invalid_argument("Invalid direct integrity window or contract");
    const auto started=ops.now_ns();if(!started)throw std::runtime_error("Direct integrity clock is unavailable");
    for(std::uint64_t offset=0;offset<bytes;) {
        const auto now=ops.now_ns();
        if(now<started||now-started>std::uint64_t(timeout_seconds)*1000000000ull)
            throw std::runtime_error("Direct integrity deadline expired");
        const auto logical=std::min<std::uint64_t>(direct_integrity_window,bytes-offset);
        const auto requested=std::size_t((logical+direct_integrity_alignment-1)&~std::uint64_t(direct_integrity_alignment-1));
        const auto got=ops.read_at(buffer,requested,offset);
        if(got!=std::int64_t(logical))throw std::runtime_error("Direct integrity read did not complete its exact original bytes");
        const auto completed=ops.now_ns();
        if(completed<now||completed-started>std::uint64_t(timeout_seconds)*1000000000ull)
            throw std::runtime_error("Direct integrity completion exceeded its deadline");
        consume(static_cast<const unsigned char*>(buffer),std::size_t(got));offset+=std::uint64_t(got);
    }
}
void verify_native_startup_file_direct(const std::string &,std::uint64_t,const std::string &,unsigned);
// Explicit CPU-only A/B control; no fallback from one read mode to another.
void verify_native_startup_file_control(const std::string &,std::uint64_t,const std::string &,unsigned,bool);
}
