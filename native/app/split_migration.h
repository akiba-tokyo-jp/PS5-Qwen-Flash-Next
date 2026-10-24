// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <utility>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
inline constexpr std::uint64_t split_migration_part_bytes=512ull<<20;
inline constexpr std::size_t split_migration_window_bytes=8u<<20;
struct SplitMigrationOps {
    virtual ~SplitMigrationOps()=default;
    virtual bool source_unchanged()=0;
    virtual void guard(const char *stage,std::uint64_t offset,std::size_t bytes)=0;
    virtual std::int64_t read_source(void *,std::size_t,std::uint64_t)=0;
    virtual bool create_pending(std::uint64_t)=0;
    // The caller owns a complete aligned window; the writer may zero padding
    // after the logical bytes for a Direct write, then trim only its new file.
    virtual std::int64_t write_pending(void *,std::size_t,std::uint64_t)=0;
    virtual bool flush_and_open_readback()=0;
    virtual std::int64_t read_pending(void *,std::size_t,std::uint64_t)=0;
    virtual bool pending_unchanged()=0;
    virtual bool publish_verified_pending(const std::string &)=0;
    virtual bool truncate_source_once(std::uint64_t)=0;
    virtual bool flush_and_record_source(std::uint64_t)=0;
};
struct SplitMigrationResult {
    std::uint64_t old_source_bytes=0,new_source_bytes=0,part_index=0,part_bytes=0;
    std::string part_sha256;
};
// No cleanup, retries or destructor-driven truncation occurs here. A caller may
// release its window only after every native call has positively returned. Any
// failure retains pending/published files and requires independent state review.
inline SplitMigrationResult migrate_verified_tail(SplitMigrationOps &ops,void *window,
        std::uint64_t source_bytes) {
    if(!window||reinterpret_cast<std::uintptr_t>(window)%16384||
       source_bytes<=split_migration_part_bytes||source_bytes>(512ull<<30))
        throw std::invalid_argument("Tail migration requires one aligned bounded window and a complete remaining source");
    const auto index=(source_bytes-1)/split_migration_part_bytes;
    const auto start=index*split_migration_part_bytes;
    const auto count=source_bytes-start;
    if(!index||!count||count>split_migration_part_bytes||!ops.source_unchanged())
        throw std::runtime_error("Tail migration source lineage is not admitted");
    ops.guard("create_pending",start,std::size_t(count));
    if(!ops.create_pending(count))throw std::runtime_error("Fresh pending tail creation was not confirmed");
    sha256_t original;sha256_init(&original);
    for(std::uint64_t done=0;done<count;) {
        const auto logical=std::size_t(std::min<std::uint64_t>(split_migration_window_bytes,count-done));
        const auto requested=(logical+16383)&~std::size_t(16383);
        ops.guard("read_source",start+done,requested);
        if(ops.read_source(window,requested,start+done)!=std::int64_t(logical))
            throw std::runtime_error("Original tail read did not return its exact bytes");
        sha256_update(&original,static_cast<const unsigned char *>(window),logical);
        ops.guard("write_pending",done,logical);
        if(ops.write_pending(window,logical,done)!=std::int64_t(logical))
            throw std::runtime_error("Pending tail write did not return exact completion");
        done+=logical;
    }
    if(!ops.source_unchanged())throw std::runtime_error("Original tail changed during copying");
    ops.guard("flush_pending",0,0);
    if(!ops.flush_and_open_readback())throw std::runtime_error("Pending tail durability or readback open was not confirmed");
    sha256_t returned;sha256_init(&returned);
    for(std::uint64_t done=0;done<count;) {
        const auto logical=std::size_t(std::min<std::uint64_t>(split_migration_window_bytes,count-done));
        const auto requested=(logical+16383)&~std::size_t(16383);
        ops.guard("read_pending",done,requested);
        if(ops.read_pending(window,requested,done)!=std::int64_t(logical))
            throw std::runtime_error("Pending tail readback did not return exact completion");
        sha256_update(&returned,static_cast<const unsigned char *>(window),logical);done+=logical;
    }
    unsigned char expected[32],actual[32];sha256_final(&original,expected);sha256_final(&returned,actual);
    for(unsigned i=0;i<32;++i)if(expected[i]!=actual[i])
        throw std::runtime_error("Pending tail full SHA256 differs from the original bytes");
    if(!ops.source_unchanged()||!ops.pending_unchanged())
        throw std::runtime_error("Tail identity changed before publication");
    std::string digest;digest.reserve(64);
    for(auto value:actual){digest.push_back("0123456789abcdef"[value>>4]);digest.push_back("0123456789abcdef"[value&15]);}
    ops.guard("publish_verified",start,std::size_t(count));
    if(!ops.publish_verified_pending(digest))throw std::runtime_error("Tail publication completion is unknown; source retained");
    if(!ops.source_unchanged()||!ops.pending_unchanged())
        throw std::runtime_error("Tail identity changed before source truncation");
    ops.guard("truncate_verified_source",start,0);
    if(!ops.truncate_source_once(start))throw std::runtime_error("Source truncation was not confirmed; never repeat it automatically");
    ops.guard("flush_truncated_source",start,0);
    if(!ops.flush_and_record_source(start))throw std::runtime_error("Truncated source durability/identity is unknown; retain the journal");
    return{source_bytes,start,index,count,std::move(digest)};
}
}
