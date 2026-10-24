// SPDX-License-Identifier: MIT
#include "shader_file.h"
#include <algorithm>
#include <cstring>
#include <limits>
#include <stdexcept>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
namespace {
constexpr unsigned char file_magic[8]={'Q','W','S','P','V','X','0','1'};
constexpr std::uint64_t verification_ns=60000000000ull,frame_ns=10000000000ull;
std::uint32_t get32(const unsigned char*p) {
    return std::uint32_t(p[0])|(std::uint32_t(p[1])<<8)|(std::uint32_t(p[2])<<16)|(std::uint32_t(p[3])<<24);
}
std::uint64_t get64(const unsigned char*p){return std::uint64_t(get32(p))|(std::uint64_t(get32(p+4))<<32);}
std::uint64_t deadline(std::uint64_t now,std::uint64_t interval) {
    if(!now||now>std::numeric_limits<std::uint64_t>::max()-interval)
        throw std::runtime_error("Shader file admission clock cannot represent its deadline");
    return now+interval;
}
}
ShaderFileLocation parse_shader_file_location(const void *token,std::size_t token_bytes,std::size_t stored,
        std::size_t original,std::uint64_t file_bytes) {
    if(!token||token_bytes!=shader_file_token_bytes||stored<48||stored>(1u<<20)||stored%4||
       original<20||original>(1u<<20)||original%4||!file_bytes||file_bytes>(512ull<<20))
        throw std::runtime_error("External shader location exceeds its exact resource contract");
    const auto*p=static_cast<const unsigned char*>(token);const auto offset=get64(p+8);
    if(std::memcmp(p,file_magic,8)||get32(p+16)!=stored||get32(p+20)!=original||offset%4||
       offset>file_bytes||stored>file_bytes-offset)
        throw std::runtime_error("External shader location differs from its immutable resource plan");
    return {offset,stored,original};
}
[[noreturn]] void ShaderFileStore::fail(const char*message){stats_.failed=true;throw std::runtime_error(message);}
ShaderFileStore::ShaderFileStore(ShaderFileOps &ops,void *window,std::size_t capacity,std::uint64_t bytes)
    :ops_(ops),window_(static_cast<unsigned char*>(window)),capacity_(capacity),file_bytes_(bytes) {
    if(!window||reinterpret_cast<std::uintptr_t>(window)%shader_file_alignment||!capacity||
       capacity%shader_file_alignment||capacity>(2u<<20)||!bytes||bytes>(512ull<<20))
        fail("External shader file requires its bounded aligned tracked window");
    sealed_=ops_.identity();if(sealed_[5]!=bytes)fail("External shader file size differs from its resource plan");
}
void ShaderFileStore::unchanged(){if(ops_.identity()!=sealed_)fail("External shader descriptor identity changed");}
std::uint64_t ShaderFileStore::time(std::uint64_t limit,std::uint64_t previous) {
    const auto now=ops_.now_ns();if(!now||now<previous||now<last_ns_||now>limit)fail("External shader file exceeded its monotonic deadline");
    last_ns_=now;return now;
}
std::size_t ShaderFileStore::fill(std::uint64_t offset,std::uint64_t limit,bool startup) {
    if(offset%shader_file_alignment||offset>=file_bytes_)fail("External shader read is not a bounded original span");
    cache_bytes_=0;ops_.system_headroom(startup);unchanged();
    const auto before=time(limit);const auto logical=std::size_t(std::min<std::uint64_t>(capacity_,file_bytes_-offset));
    ops_.before_read();stats_.read_pending=true;
    const auto got=ops_.read_at(window_,capacity_,offset);
    stats_.read_pending=false;++stats_.read_calls;ops_.read_returned();
    if(got!=std::int64_t(logical))fail("External shader read did not return its exact EOF-bounded bytes");
    (void)time(limit,before);unchanged();
    stats_.returned_bytes+=logical;cache_offset_=offset;cache_bytes_=logical;return logical;
}
void ShaderFileStore::verify(const std::array<unsigned char,32>&expected) {
    if(stats_.failed||stats_.verified||stats_.read_pending)fail("External shader verification cannot repeat or reuse failed work");
    try {
        const auto limit=deadline(time(std::numeric_limits<std::uint64_t>::max()),verification_ns);unchanged();sha256_t hash;sha256_init(&hash);
        for(std::uint64_t offset=0;offset<file_bytes_;) {
            const auto bytes=fill(offset,limit,true);sha256_update(&hash,window_,bytes);offset+=bytes;
        }
        std::array<unsigned char,32> actual{};sha256_final(&hash,actual.data());
        if(actual!=expected)fail("Complete external shader file SHA256 differs from its resource plan");
        unchanged();(void)time(limit);stats_.verified=true;
    }catch(...){stats_.failed=true;throw;}
}
const unsigned char *ShaderFileStore::frame(std::uint64_t offset,std::size_t bytes) {
    if(stats_.failed||!stats_.verified||stats_.read_pending)fail("External shader input requires positive current whole-file verification");
    try {
        if(!bytes||bytes>(1u<<20)||offset%4||bytes%4||offset>file_bytes_||bytes>file_bytes_-offset)
            fail("External shader frame exceeds its complete immutable file");
        const auto aligned=offset&~std::uint64_t(shader_file_alignment-1),inset=offset-aligned;
        if(inset>capacity_||bytes>capacity_-inset)fail("External shader frame exceeds its one bounded input window");
        const auto limit=deadline(time(std::numeric_limits<std::uint64_t>::max()),frame_ns);ops_.system_headroom(false);unchanged();
        if(offset<cache_offset_||offset-cache_offset_>cache_bytes_||bytes>cache_bytes_-(offset-cache_offset_))
            (void)fill(aligned,limit,false);
        if(offset<cache_offset_||offset-cache_offset_>cache_bytes_||bytes>cache_bytes_-(offset-cache_offset_))
            fail("External shader read did not cover the complete requested frame");
        (void)time(limit);++stats_.frame_requests;return window_+(offset-cache_offset_);
    }catch(...){stats_.failed=true;throw;}
}
}
