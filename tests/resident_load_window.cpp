// SPDX-License-Identifier: MIT
// Exact source-byte and submission-count checks; no learned host inference.
#include "resident-mapped-source.private.h"
#include <cstdlib>
#include <iostream>
#include <map>
using namespace qwen_app;
struct Ops final:SourceReadOps {
    SourceFile file{"original",(9u<<20)+1000,{1,1,0100444,1,0,(9u<<20)+1000,1,0,1,0}};
    unsigned calls=0;std::size_t maximum=0;bool short_read=false;
    SourceIdentity identity(int)override{return file.identity;}
    int open_direct(const std::string &path)override{if(path!=file.path)throw std::runtime_error("Wrong source");return 7;}
    bool close_file(int fd)override{return fd==7;}
    std::uint64_t system_headroom()override{return 1ull<<30;}
    std::int64_t read_at(int,void *to,std::size_t bytes,std::uint64_t offset)override{
        if(offset%model_read_alignment||bytes%model_read_alignment||bytes>model_read_window)
            throw std::runtime_error("Unaligned source request");
        ++calls;maximum=std::max(maximum,bytes);
        const auto count=std::min<std::uint64_t>(bytes,file.bytes-offset);
        auto *p=static_cast<unsigned char *>(to);for(std::size_t i=0;i<count;++i)p[i]=(offset+i)%251;
        return std::int64_t(count)-(short_read?1:0);
    }
};
int main() {
    std::vector<unsigned char> memory(model_read_window+model_read_alignment);
    const auto at=(reinterpret_cast<std::uintptr_t>(memory.data())+model_read_alignment-1)&~std::uintptr_t(model_read_alignment-1);
    Ops ops;ResidentMappedSourceReader reader({ops.file},ops,reinterpret_cast<void *>(at));
    constexpr std::uintptr_t key=1ull<<40;reader.preflight();reader.register_mapping(key,ops.file.bytes,7);
    for(unsigned phase=0;phase<3;++phase) {
        const std::size_t limit=phase==1?1u<<20:model_read_window;
        reader.set_resident_load_limit(limit);ops.maximum=0;const auto before=ops.calls;
        for(std::size_t done=0;done<(9u<<20);){std::size_t copied=0;
            const auto *data=static_cast<const unsigned char *>(reader.prepare(key+123+done,(9u<<20)-done,copied));
            if(!copied||copied>limit)throw std::runtime_error("Load-only read bound changed");
            for(std::size_t i=0;i<copied;++i)if(data[i]!=(123+done+i)%251)throw std::runtime_error("Original source byte changed");
            reader.completed();done+=copied;}
        if(ops.maximum>limit||ops.calls-before!=(phase==1?10u:2u))throw std::runtime_error("Actual read-call accounting differs");
    }
    bool refused=false;try{reader.set_resident_load_limit(123);}catch(const std::invalid_argument &){refused=true;}
    if(!refused)throw std::runtime_error("Unsupported load window admitted");
    const auto stats=reader.stats();if(stats.chunks!=stats.completed_windows||stats.physical_read_calls!=ops.calls)
        throw std::runtime_error("Actual source completion or physical calls differ");
    reader.before_unmap(key,ops.file.bytes);reader.after_unmap(key,ops.file.bytes);reader.close_completed();
    Ops short_ops;ResidentMappedSourceReader failed({short_ops.file},short_ops,reinterpret_cast<void *>(at));
    failed.register_mapping(key,short_ops.file.bytes,7);failed.set_resident_load_limit(1u<<20);short_ops.short_read=true;refused=false;
    try{std::size_t copied;failed.prepare(key,1u<<20,copied);}catch(const std::runtime_error &){refused=true;}
    if(!refused||short_ops.calls!=1)throw std::runtime_error("A short read was retried or accepted");
    std::cout<<"{\"original_bytes_verified\":28311552,\"8MiB_1MiB_8MiB_transition\":true,\"physical_calls_exact\":true,\"short_read_refused_without_retry\":true}\n";
}
