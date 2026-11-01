// SPDX-License-Identifier: GPL-3.0-or-later
// All numeric addresses below are synthetic encoding inputs, never dereferenced.
#include "apr_command_encoder.h"
#include <array>
#include <cassert>
#include <cstdio>
int main(){
    alignas(16)std::array<std::uint32_t,64>w{};qwen_app::AprCommandBuffer cb;
    assert(qwen_app::apr_bind(cb,w.data(),sizeof(w)));
    const std::uint32_t expected[]={0x428,0x3fff,0x1234,0x56789000,0x1234};
    assert(qwen_app::apr_read(cb,0x1234,reinterpret_cast<void*>(UINT64_C(0x123456789000)),16384,0));
    for(unsigned i=0;i<5;++i)assert(w[i]==expected[i]);
    for(const auto offset:{UINT64_C(0x3ffff),UINT64_C(0x100000000),UINT64_C(0xffffffffff)}){
        assert(qwen_app::apr_bind(cb,w.data(),sizeof(w)));
        assert(qwen_app::apr_read(cb,7,reinterpret_cast<void*>(UINT64_C(0x123456789000)),UINT64_C(0x100000000),offset));
        auto decoded=std::uint64_t((w[0]&0x3ffff000u)>>12)|(w[4]&0xfffc0000u);
        if(cb.offset==24)decoded|=std::uint64_t(w[5])<<32;
        assert(decoded==offset&&std::uint64_t(w[1])+1==UINT64_C(0x100000000));
    }
    for(const auto value:{UINT64_C(0),UINT64_C(3),UINT64_C(4),UINT64_C(0x3ffffffff),UINT64_C(0x400000000),UINT64_MAX}){
        assert(qwen_app::apr_bind(cb,w.data(),sizeof(w)));
        assert(qwen_app::apr_completion(cb,reinterpret_cast<volatile std::uint64_t*>(UINT64_C(0x102030405060)),value));
        auto decoded=std::uint64_t((w[0]>>12)&3u);
        if(cb.offset>=12)decoded|=std::uint64_t(w[2])<<2;
        if(cb.offset==16)decoded|=std::uint64_t(w[3])<<34;
        assert(decoded==value&&((std::uint64_t(w[0]&0xffff0000u)<<16)|(w[1]&0xfffffff8u))==UINT64_C(0x102030405060));
    }
    assert(qwen_app::apr_bind(cb,w.data(),16));w[4]=0x91ab7321;
    assert(!qwen_app::apr_read(cb,1,reinterpret_cast<void*>(16384),16384,0));assert(!cb.offset&&!cb.commands&&w[4]==0x91ab7321);
    assert(!qwen_app::apr_read(cb,1,reinterpret_cast<void*>(16384),0,0));
    assert(!qwen_app::apr_read(cb,1,reinterpret_cast<void*>(16384),1,UINT64_C(1)<<40));
    assert(!qwen_app::apr_completion(cb,reinterpret_cast<volatile std::uint64_t*>(3),1));
    std::puts("APR public read/completion encoding checks passed");
}
