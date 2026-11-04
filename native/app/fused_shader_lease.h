// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
struct FusedShaderSource {
    const void*original;std::size_t original_stored,original_decoded;
    const void*replacement;std::size_t replacement_bytes;
    const unsigned char*replacement_SHA256;
};
struct FusedShaderOps {
    const void*(*prepare)(const void*,std::size_t,std::size_t*,void**);
    void(*complete)(void*);
    bool(*digest)(const void*,std::size_t,const unsigned char*);
};
inline const void*prepare_fused_shader(const void*storage,std::size_t bytes,std::size_t*decoded,void**lease,
    const FusedShaderSource&source,const FusedShaderOps&ops){
    if(!ops.prepare)throw std::runtime_error("The original shader admission provider is required");
    if(storage!=source.replacement)return ops.prepare(storage,bytes,decoded,lease);
    if(!decoded||!lease||bytes!=source.replacement_bytes||bytes<20||bytes>(1u<<20)||bytes%4||
       !storage||reinterpret_cast<std::uintptr_t>(storage)%4||!source.original||!source.original_stored||!source.original_decoded||!source.replacement_SHA256||
       !ops.prepare||!ops.complete||!ops.digest)
        throw std::runtime_error("Exact aligned application shader and original CPU admission required");
    std::size_t old_bytes=0;
    // This preserves the selected original codec/file readiness and its exact
    // owner lease. An exception from that provider retains unknown ownership.
    const void*original=ops.prepare(source.original,source.original_stored,&old_bytes,lease);
    if(!original||old_bytes!=source.original_decoded||!ops.digest(storage,bytes,source.replacement_SHA256)){
        if(*lease){ops.complete(*lease);*lease=nullptr;}
        throw std::runtime_error("Original shader admission or new static shader SHA256 failed");
    }
    *decoded=bytes;return storage;
}
}
