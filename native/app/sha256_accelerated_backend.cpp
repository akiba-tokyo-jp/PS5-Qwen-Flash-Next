// SPDX-License-Identifier: MIT
// Optional CPU-only converter backend. The original SHA ABI, padding and
// scalar fallback stay intact. Hardware dispatch requires measured CPU bits.
#include <algorithm>
#include <cstring>
#include <cpuid.h>
#include "../../third_party/sha-intrinsics/sha256-x86.c"
extern "C" {
#define sha256_update qwen_sha256_scalar_update
#define sha256_hash qwen_sha256_scalar_hash
#include "hash/sha256/sha256.c"
#undef sha256_update
#undef sha256_hash
}
#if defined(_WIN32)
#define QWEN_SHA_EXPORT __declspec(dllexport)
#else
#define QWEN_SHA_EXPORT __attribute__((visibility("default")))
#endif
extern "C" QWEN_SHA_EXPORT unsigned qwen_sha256_acceleration_available(){
    static const bool available=[] {
        unsigned a=0,b=0,c=0,d=0;
        if(!__get_cpuid(1,&a,&b,&c,&d)||!(c&(1u<<9))||!(c&(1u<<19)))return false;
        return __get_cpuid_count(7,0,&a,&b,&c,&d)&&(b&(1u<<29));
    }();
    return available;
}
extern "C" QWEN_SHA_EXPORT void sha256_update(sha256_t*p,const unsigned char*data,std::size_t size){
    if(!qwen_sha256_acceleration_available()){qwen_sha256_scalar_update(p,data,size);return;}
    auto partial=std::size_t(p->count&63);
    if(partial&&size){const auto n=std::min(size,64-partial);std::memcpy(p->buffer+partial,data,n);
        p->count+=n;data+=n;size-=n;partial+=n;
        if(partial==64)sha256_process_x86(p->state,p->buffer,64);
    }
    while(size>=64){
        // The example's length is 32 bits; split large callers without
        // truncation. Conversion calls remain bounded by eight MiB.
        const auto n=std::min<std::size_t>(size&~std::size_t(63),UINT32_MAX&~std::size_t(63));
        sha256_process_x86(p->state,data,static_cast<std::uint32_t>(n));p->count+=n;data+=n;size-=n;
    }
    if(size){std::memcpy(p->buffer+(p->count&63),data,size);p->count+=size;}
}
extern "C" QWEN_SHA_EXPORT void sha256_hash(unsigned char*out,const unsigned char*data,std::size_t size){
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,data,size);sha256_final(&hash,out);
}
