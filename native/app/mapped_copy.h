// SPDX-License-Identifier: MIT
#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <immintrin.h>
namespace qwen_app {
// Internal byte-copy candidate only. The existing Vulkan caller must prove
// destination ownership, bounds and HOST_VISIBLE | HOST_COHERENT properties.
// This helper never admits arbitrary pointers or changes allocation policy.
inline std::atomic<bool> mapped_copy_configured{false},mapped_copy_scope{false};
inline std::atomic<std::uint64_t> mapped_copy_streamed_bytes{0},mapped_copy_streamed_calls{0};
inline void configure_mapped_copy(bool enabled){mapped_copy_configured.store(enabled);}
inline void set_mapped_copy_scope(bool enabled){mapped_copy_scope.store(enabled);}
struct MappedCopyStats {std::uint64_t bytes=0,calls=0;};
inline MappedCopyStats mapped_copy_stats(){return {mapped_copy_streamed_bytes.load(),mapped_copy_streamed_calls.load()};}
__attribute__((target("avx2"))) inline void stream_mapped_copy_body(void *destination,const void *source,std::size_t bytes) {
    auto *dst=static_cast<unsigned char *>(destination);const auto *src=static_cast<const unsigned char *>(source);
    // Whole cache lines avoid mixing temporal/streaming stores in one line.
    const auto prefix=(64-reinterpret_cast<std::uintptr_t>(dst)%64)%64;
    if(prefix){std::memcpy(dst,src,prefix);dst+=prefix;src+=prefix;bytes-=prefix;}
    const auto bulk=bytes&~std::size_t(63);
    for(std::size_t i=0;i<bulk;i+=64) {
        const auto first=_mm256_loadu_si256(reinterpret_cast<const __m256i *>(src+i));
        const auto second=_mm256_loadu_si256(reinterpret_cast<const __m256i *>(src+i+32));
        _mm256_stream_si256(reinterpret_cast<__m256i *>(dst+i),first);
        _mm256_stream_si256(reinterpret_cast<__m256i *>(dst+i+32),second);
    }
    _mm_sfence();_mm256_zeroupper();
    if(bytes!=bulk)std::memcpy(dst+bulk,src+bulk,bytes-bulk);
}
inline bool try_streaming_mapped_copy(void *destination,const void *source,std::size_t bytes) {
    if(!mapped_copy_configured.load()||!mapped_copy_scope.load()||bytes<(1u<<20)||!destination||!source)return false;
    const auto dst=reinterpret_cast<std::uintptr_t>(destination),src=reinterpret_cast<std::uintptr_t>(source);
    const auto limit=std::numeric_limits<std::uintptr_t>::max();
    if(bytes>limit-dst||bytes>limit-src||(dst<src+bytes&&src<dst+bytes))return false;
    stream_mapped_copy_body(destination,source,bytes);
    mapped_copy_streamed_bytes.fetch_add(bytes);mapped_copy_streamed_calls.fetch_add(1);
    return true;
}
}
extern "C" bool qwen_app_try_streaming_model_window(void *,const void *,std::size_t);
