// SPDX-License-Identifier: MIT
#include "shader_file.h"
#include <algorithm>
#include <cstring>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
}
using namespace qwen_app;
namespace {
void check(bool value,const char*message){if(!value)throw std::runtime_error(message);}
template<class F>void refused(F action){bool failed=false;try{action();}catch(const std::exception&){failed=true;}check(failed,"Unsafe shader-file operation was admitted");}
std::array<unsigned char,32> digest(const std::vector<unsigned char>&data) {
    sha256_t hash;sha256_init(&hash);sha256_update(&hash,data.data(),data.size());
    std::array<unsigned char,32> value{};sha256_final(&hash,value.data());return value;
}
struct Ops final:ShaderFileOps {
    std::vector<unsigned char> source=std::vector<unsigned char>(65557);
    std::uint64_t clock=1000,delay=100,version=1,calls=0,begin=0,returned=0,initial_guards=0,frame_guards=0;
    int failure=0;bool identity_during_read=false;void*expected_window=nullptr;
    Ops(){for(std::size_t i=0;i<source.size();++i)source[i]=static_cast<unsigned char>(i*31+i/251);}
    std::array<std::uint64_t,10> identity()override{return {1,version,0100600,1,1,source.size(),11,0,11,0};}
    void system_headroom(bool startup)override{if(startup)++initial_guards;else ++frame_guards;if(failure==6)throw std::runtime_error("Synthetic pressure");}
    std::uint64_t now_ns()override{return clock;}
    void before_read()override{++begin;if(failure==7)throw std::runtime_error("Synthetic before-marker failure");}
    std::int64_t read_at(void*at,std::size_t bytes,std::uint64_t offset)override {
        check(at==expected_window&&offset%16384==0&&bytes==49152,"Actual bounded read recipe changed");++calls;
        if(failure==4)throw std::runtime_error("Synthetic unknown read completion");
        if(failure==3)return -1;
        const auto logical=std::min<std::uint64_t>(bytes,source.size()-offset);
        std::memcpy(at,source.data()+offset,logical);clock+=delay;if(identity_during_read)++version;
        return static_cast<std::int64_t>(logical)+(failure==1?-4:failure==2?1:0);
    }
    void read_returned()override{++returned;if(failure==5)throw std::runtime_error("Synthetic returned-marker failure");}
};
struct Fixture {
    Ops ops;std::vector<unsigned char> backing=std::vector<unsigned char>(49152+32768,0xa5);
    unsigned char*window=nullptr;std::unique_ptr<ShaderFileStore> file;
    Fixture(){auto base=reinterpret_cast<std::uintptr_t>(backing.data()+64);window=reinterpret_cast<unsigned char*>((base+16383)&~std::uintptr_t(16383));ops.expected_window=window;file=std::make_unique<ShaderFileStore>(ops,window,49152,ops.source.size());}
    void guards(){for(unsigned i=0;i<64;++i)check(window[-int(i)-1]==0xa5&&window[49152+i]==0xa5,"Shader-file input exceeded its sole tracked window");}
    void verify(){file->verify(digest(ops.source));guards();}
    void no_retry(){const auto calls=ops.calls;refused([&]{file->frame(16,128);});check(ops.calls==calls&&file->stats().failed,"Failed shader input retried");guards();}
};
void put32(unsigned char*p,std::uint32_t value){for(unsigned i=0;i<4;++i)p[i]=static_cast<unsigned char>(value>>(8*i));}
}
int main(){try {
    {Fixture f;f.verify();check(f.file->stats().verified&&f.ops.calls==2&&f.file->stats().returned_bytes==65557,"Full-file SHA or exact EOF verification changed");
     auto before=f.ops.calls;const auto*hit=f.file->frame(49160,128);check(f.ops.calls==before&&!std::memcmp(hit,f.ops.source.data()+49160,128),"Verified cached frame changed");
     const auto*first=f.file->frame(16,128);check(f.ops.calls==before+1&&!std::memcmp(first,f.ops.source.data()+16,128),"Frame miss changed original bytes");
     const auto*cross=f.file->frame(49080,512);check(!std::memcmp(cross,f.ops.source.data()+49080,512),"Aligned spanning frame changed original bytes");
     check(f.ops.initial_guards==2&&f.ops.frame_guards>=3&&!f.file->stats().read_pending,"Memory admission or positive read completion was omitted");f.guards();}
    {Fixture f;refused([&]{f.file->frame(16,128);});check(f.ops.calls==0,"Unverified source was read");f.no_retry();}
    {Fixture f;auto expected=digest(f.ops.source);expected[0]^=1;refused([&]{f.file->verify(expected);});check(!f.file->stats().verified,"Wrong whole-file digest admitted");f.no_retry();}
    {Fixture f;f.verify();auto calls=f.ops.calls;refused([&]{f.verify();});check(f.ops.calls==calls,"Whole-file verification repeated");f.no_retry();}
    for(int mode=1;mode<=7;++mode){Fixture f;f.ops.failure=mode;refused([&]{f.verify();});
        check(f.file->stats().read_pending==(mode==4),"Unknown read completion was misclassified");
        check(f.ops.calls==(mode==6||mode==7?0u:1u),"Read refusal issued an extra operation");f.ops.failure=0;f.no_retry();}
    for(unsigned mode=0;mode<6;++mode){Fixture f;f.verify();auto calls=f.ops.calls;
        std::uint64_t offset=mode==0?std::numeric_limits<std::uint64_t>::max()-3:mode==1?65556:mode==2?1:16;
        std::size_t bytes=mode==3?0:mode==4?3:mode==5?49152:128;
        refused([&]{f.file->frame(offset,bytes);});check(f.ops.calls==calls,"Invalid span started I/O");f.no_retry();}
    {Fixture f;f.verify();++f.ops.version;auto calls=f.ops.calls;refused([&]{f.file->frame(16,128);});check(f.ops.calls==calls,"Changed identity was read");f.no_retry();}
    {Fixture f;f.ops.identity_during_read=true;refused([&]{f.verify();});check(f.ops.calls==1&&!f.file->stats().read_pending,"Changed descriptor retained a false pending read");f.no_retry();}
    for(auto delay:{31000000000ull,61000000000ull}){Fixture f;f.ops.delay=delay;refused([&]{f.verify();});check(f.ops.calls==(delay>60000000000ull?1u:2u),"Whole-file deadline reset between reads");f.no_retry();}
    {Fixture f;f.verify();f.ops.delay=11000000000ull;refused([&]{f.file->frame(16,128);});f.no_retry();}
    {Fixture f;f.verify();f.ops.clock=1;auto calls=f.ops.calls;refused([&]{f.file->frame(16,128);});check(f.ops.calls==calls,"Backwards clock issued I/O");f.no_retry();}
    {Fixture f;f.ops.clock=0;refused([&]{f.verify();});check(f.ops.calls==0,"Unavailable clock issued I/O");f.no_retry();}
    {Ops ops;std::vector<unsigned char> memory(49152);refused([&]{ShaderFileStore invalid(ops,memory.data()+1,49152,ops.source.size());});check(ops.calls==0,"Misaligned window issued I/O");}
    for(unsigned mode=0;mode<9;++mode){std::array<unsigned char,24> token{};std::memcpy(token.data(),"QWSPVX01",8);put32(token.data()+8,64);put32(token.data()+16,64);put32(token.data()+20,256);
        auto parse=[&]{return parse_shader_file_location(token.data(),mode==1?20:24,64,256,65557);};
        if(mode==0){const auto r=parse();check(r.offset==64&&r.bytes==64&&r.original_bytes==256,"Valid resource location changed");continue;}
        if(mode==2)token[0]^=1;if(mode==3)put32(token.data()+8,65);if(mode==4)std::memset(token.data()+8,0xff,8);
        if(mode==5)put32(token.data()+16,68);if(mode==6)put32(token.data()+20,252);if(mode==7)put32(token.data()+8,65520);
        if(mode==8)put32(token.data()+8,65556);refused(parse);
    }
    std::cout<<"Actual external shader file SHA, cache spans, EOF, clocks, identity, canaries and retained no-retry failures passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
