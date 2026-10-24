// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
namespace qwen_app {
inline constexpr std::size_t shader_file_alignment=16384;
inline constexpr std::size_t shader_file_token_bytes=24;
struct ShaderFileLocation {std::uint64_t offset;std::size_t bytes,original_bytes;};
ShaderFileLocation parse_shader_file_location(const void *,std::size_t,std::size_t,std::size_t,std::uint64_t);
struct ShaderFileOps {
    virtual ~ShaderFileOps()=default;
    virtual std::array<std::uint64_t,10> identity()=0;
    virtual void system_headroom(bool startup)=0;
    virtual std::uint64_t now_ns()=0;
    virtual void before_read()=0;
    virtual std::int64_t read_at(void *,std::size_t,std::uint64_t)=0;
    virtual void read_returned()=0;
};
struct ShaderFileStats {
    std::uint64_t read_calls=0,returned_bytes=0,frame_requests=0;
    bool verified=false,failed=false,read_pending=false;
};
// The caller owns one aligned tracked buffer and its descriptor. Calls require
// the exclusive codec lease. Failure retains all backing; this class never
// closes, frees, reclaims, retries, or cancels an opaque read.
class ShaderFileStore {
    ShaderFileOps &ops_;
    unsigned char *window_;
    std::size_t capacity_;
    std::uint64_t file_bytes_,cache_offset_=0,cache_bytes_=0,last_ns_=0;
    std::array<std::uint64_t,10> sealed_;
    ShaderFileStats stats_;
    [[noreturn]] void fail(const char *);
    void unchanged();
    std::uint64_t time(std::uint64_t,std::uint64_t=0);
    std::size_t fill(std::uint64_t,std::uint64_t,bool);
public:
    ShaderFileStore(ShaderFileOps &,void *,std::size_t,std::uint64_t);
    void verify(const std::array<unsigned char,32> &);
    const unsigned char *frame(std::uint64_t,std::size_t);
    const ShaderFileStats &stats()const{return stats_;}
};
}
