// SPDX-License-Identifier: MIT
// Synchronous exact restoration. No GPU, file I/O, threads or implicit allocator.
#pragma once
#include "driver_tables.h"
#include "../thirdparty/zlib/zlib.h"
#include <cstdint>
#include <cstring>
extern "C" {
#include "hash/sha256/sha256.h"
}
namespace qwen_app {
using DriverTableProtect=int (*)(void *,std::size_t);
inline bool restore_driver_tables(const qwen_driver_table_plan &p,alloc_func allocate,free_func release,
                                 void *opaque,DriverTableProtect protect) {
    const auto begin=reinterpret_cast<std::uintptr_t>(p.begin),end=reinterpret_cast<std::uintptr_t>(p.end);
    if(!p.tables||!p.packed||!allocate||!release||!protect||!p.count||p.count>1024||!begin||end<=begin||
       begin%16384||end%16384||end-begin>(16u<<20)||!p.packed_bytes||p.packed_bytes>(4u<<20))return false;
    std::size_t previous=0;
    for(std::size_t i=0;i<p.count;++i) {
        const auto &t=p.tables[i];const auto at=reinterpret_cast<std::uintptr_t>(t.target);
        if(at<begin||at>=end||!t.bytes||t.bytes>end-at||t.bytes>UINT32_MAX||
           t.offset!=previous||!t.packed_bytes||t.packed_bytes>p.packed_bytes-previous)return false;
        for(std::size_t j=0;j<i;++j) {
            const auto other=reinterpret_cast<std::uintptr_t>(p.tables[j].target);
            if(at<other+p.tables[j].bytes&&other<at+t.bytes)return false;
        }
        previous+=t.packed_bytes;
    }
    if(previous!=p.packed_bytes)return false;
    z_stream stream{};stream.zalloc=allocate;stream.zfree=release;stream.opaque=opaque;
    if(inflateInit(&stream)!=Z_OK)return false;
    bool ok=true;
    for(std::size_t i=0;i<p.count&&ok;++i) {
        const auto &t=p.tables[i];
        if(inflateReset(&stream)!=Z_OK){ok=false;break;}
        stream.next_in=const_cast<Bytef *>(p.packed+t.offset);stream.avail_in=static_cast<uInt>(t.packed_bytes);
        stream.next_out=t.target;stream.avail_out=static_cast<uInt>(t.bytes);
        ok=inflate(&stream,Z_FINISH)==Z_STREAM_END&&stream.total_in==t.packed_bytes&&stream.total_out==t.bytes;
        if(ok){sha256_t h;unsigned char digest[32];sha256_init(&h);sha256_update(&h,t.target,t.bytes);sha256_final(&h,digest);
            ok=!std::memcmp(digest,t.sha256,sizeof(digest));}
    }
    if(inflateEnd(&stream)!=Z_OK)ok=false;
    return ok&&protect(p.begin,end-begin)==0;
}
}
