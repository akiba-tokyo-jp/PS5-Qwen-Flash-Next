// SPDX-License-Identifier: MIT
// Dedicated resident experiment. The ordinary production restorer is unchanged.
// Preserve original table geometry, exact output hashes and readonly protection;
// bound each output call to one kernel page instead of pricing all future work.
#pragma once
#include "driver_table_restore.h"
#include <ps5platform/heap.h>
#include <sys/mman.h>
namespace qwen_app {
struct ResidentTableMemory {
    struct Slot {void *p=nullptr;std::size_t bytes=0;};
    std::array<Slot,8> slots{};std::size_t live=0;
    std::uint64_t before=0,minimum=UINT64_MAX,after=0,chunks=0,bytes=0,tables=0;
    bool fault=false,memory_refused=false,completed=false;
    bool permit(unsigned additional=20) noexcept {
        try {
            const auto m=admit_native_system_memory();
            minimum=std::min(minimum,std::uint64_t(m.kernel_free));after=m.kernel_free;
            const auto required=std::uint64_t(m.kernel_minimum)+std::max<std::uint64_t>(m.kernel_reserved,256)+additional;
            if(m.page_size!=16384||m.flexible_available<(264ull<<20)){fault=true;return false;}
            if(m.kernel_free<required){memory_refused=true;return false;}
            return true;
        }catch(const KernelMemoryPressure&){memory_refused=true;return false;}
        catch(...){fault=true;return false;}
    }
};
static voidpf resident_table_allocate(voidpf opaque,uInt n,uInt bytes) noexcept {
    auto &s=*static_cast<ResidentTableMemory*>(opaque);
    if(!n||!bytes||std::size_t(n)>(1u<<20)/bytes||std::size_t(n)*bytes>(1u<<20)-s.live||!s.permit(19))return nullptr;
    for(auto &slot:s.slots)if(!slot.p) {
        slot.bytes=std::size_t(n)*bytes;slot.p=ps5_heap_calloc(n,bytes);
        if(!slot.p||!ps5_heap_owns(slot.p)){s.fault=true;return nullptr;}
        s.live+=slot.bytes;return slot.p;
    }
    s.fault=true;return nullptr;
}
static void resident_table_release(voidpf opaque,voidpf p) noexcept {
    auto &s=*static_cast<ResidentTableMemory*>(opaque);
    for(auto &slot:s.slots)if(p&&slot.p==p&&ps5_heap_owns(p)) {
        ps5_heap_free(p);s.live-=slot.bytes;slot={};return;
    }
    s.fault=true;
}
static ResidentTableMemory restore_resident_tables_incrementally() {
    static bool attempted=false;ResidentTableMemory result;
    if(attempted||!&qwen_driver_table_storage){result.fault=true;return result;}attempted=true;
    const auto &p=qwen_driver_table_storage;
    const auto begin=reinterpret_cast<std::uintptr_t>(p.begin),end=reinterpret_cast<std::uintptr_t>(p.end);
    if(!p.tables||!p.packed||!p.count||p.count>1024||!begin||end<=begin||begin%16384||end%16384||
       end-begin>(16u<<20)||!p.packed_bytes||p.packed_bytes>(4u<<20)){result.fault=true;return result;}
    std::size_t previous=0;
    for(std::size_t i=0;i<p.count;++i) {
        const auto &t=p.tables[i];const auto at=reinterpret_cast<std::uintptr_t>(t.target);
        if(at<begin||at>=end||!t.bytes||t.bytes>end-at||t.bytes>UINT32_MAX||t.offset!=previous||
           !t.packed_bytes||previous>p.packed_bytes||t.packed_bytes>p.packed_bytes-previous){result.fault=true;return result;}
        for(std::size_t j=0;j<i;++j) {
            const auto other=reinterpret_cast<std::uintptr_t>(p.tables[j].target);
            if(at<other+p.tables[j].bytes&&other<at+t.bytes){result.fault=true;return result;}
        }
        previous+=t.packed_bytes;
    }
    if(previous!=p.packed_bytes||!result.permit())return result;
    result.before=result.after;
    z_stream stream{};stream.zalloc=resident_table_allocate;stream.zfree=resident_table_release;stream.opaque=&result;
    if(inflateInit(&stream)!=Z_OK)return result;
    bool ok=true;
    for(std::size_t i=0;i<p.count&&ok;++i) {
        const auto &t=p.tables[i];if(inflateReset(&stream)!=Z_OK){ok=false;break;}
        stream.next_in=const_cast<Bytef*>(p.packed+t.offset);stream.avail_in=static_cast<uInt>(t.packed_bytes);
        int status=Z_OK;
        while(stream.total_out<t.bytes&&ok) {
            if(!result.permit()){ok=false;break;}
            const auto at=reinterpret_cast<std::uintptr_t>(t.target)+stream.total_out;
            const auto step=std::min<std::size_t>(16384-(at%16384),t.bytes-stream.total_out);
            const auto before=stream.total_out;
            stream.next_out=t.target+before;stream.avail_out=static_cast<uInt>(step);
            status=inflate(&stream,Z_NO_FLUSH);++result.chunks;result.bytes+=stream.total_out-before;
            if((status!=Z_OK&&status!=Z_STREAM_END)||stream.total_out<=before||
               (status==Z_STREAM_END&&stream.total_out!=t.bytes))ok=false;
        }
        if(ok&&status!=Z_STREAM_END) {
            unsigned char terminator=0;stream.next_out=&terminator;stream.avail_out=1;
            if(!result.permit()||inflate(&stream,Z_FINISH)!=Z_STREAM_END)ok=false;
        }
        ok=ok&&stream.total_in==t.packed_bytes&&stream.total_out==t.bytes;
        if(ok) {
            sha256_t h;unsigned char digest[32];sha256_init(&h);sha256_update(&h,t.target,t.bytes);sha256_final(&h,digest);
            ok=!std::memcmp(digest,t.sha256,sizeof(digest));if(ok)++result.tables;
        }
    }
    if(inflateEnd(&stream)!=Z_OK||result.fault||result.live)ok=false;
    if(ok)ok=result.permit()&&mprotect(p.begin,end-begin,PROT_READ)==0;
    result.completed=ok&&result.tables==p.count;return result;
}
}
