// SPDX-License-Identifier: MIT
#include "direct_bmp.h"
#include <vector>
#include <iostream>
using namespace qwen_app;
static void check(bool ok){if(!ok)throw std::runtime_error("Direct BMP control failed");}
struct Source {
    void copy_row(unsigned y,std::size_t at,unsigned char *out,std::size_t n) {
        check(y<frame_height && at+n<=frame_row_bytes);
        for(std::size_t i=0;i<n;++i)out[i]=static_cast<unsigned char>(((at+i)/4+13*y+((at+i)%4)*37)%251);
    }
};
struct Sink {
    std::vector<unsigned char> bytes;unsigned calls=0;int fail=0;std::uint64_t clock=1;bool finished=false;
    std::uint64_t now_ns(){if(fail==3 && calls)clock+=9000000000ull;return clock++;}
    std::int64_t write(void *p,std::size_t n){
        check(reinterpret_cast<std::uintptr_t>(p)%frame_write_alignment==0 && n && n<=frame_write_window && n%frame_write_alignment==0);
        ++calls;if(fail==1)return -1;if(fail==2)return n-1;
        const auto *b=static_cast<const unsigned char*>(p);bytes.insert(bytes.end(),b,b+n);return n;
    }
    void finish(std::uint64_t n){check(n==frame_bmp_bytes);if(fail==4)throw std::runtime_error("Injected commit refusal");
        for(std::size_t i=n;i<bytes.size();++i)check(bytes[i]==0);bytes.resize(n);finished=true;}
};
int main(){
    std::vector<unsigned char> allocation(frame_write_window+frame_write_alignment);
    void *window=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(allocation.data())+frame_write_alignment-1)&~std::uintptr_t(frame_write_alignment-1));
    Source source;Sink sink;stream_direct_bmp(source,sink,window);check(sink.finished && sink.calls==8);
    const auto header=frame_bmp_header();check(std::equal(header.begin(),header.end(),sink.bytes.begin()));
    for(unsigned y=0;y<frame_height;++y)for(std::size_t x=0;x<frame_row_bytes;++x)
        check(sink.bytes[54+std::size_t(y)*frame_row_bytes+x]==(x/4+13*(frame_height-1-y)+(x%4)*37)%251);
    for(int fail=1;fail<=4;++fail){Sink bad;bad.fail=fail;bool refused=false;
        try{stream_direct_bmp(source,bad,window);}catch(const std::exception &){refused=true;}
        check(refused && !bad.finished);if(fail<4)check(bad.calls==1);}
    Sink invalid;bool refused=false;try{stream_direct_bmp(source,invalid,static_cast<unsigned char*>(window)+1);}catch(const std::exception&){refused=true;}
    check(refused && invalid.calls==0);std::cout<<"Exact 8294454-byte BMP, zero padding, bounded writes and five refusal controls passed\n";
}
