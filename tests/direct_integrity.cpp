// SPDX-License-Identifier: MIT
// Exercise the actual aligned streaming algorithm with exact EOF, no retry and deadline controls.
#include "direct_integrity.h"
#include <fstream>
#include <iostream>
#include <cstring>
#include <vector>
extern "C" {
#include "hash/sha256/sha256.h"
}
using namespace qwen_app;
static void check(bool value,const char * message){if(!value)throw std::runtime_error(message);}
template<class F> static void rejects(F f){bool failed=false;try{f();}catch(const std::exception&){failed=true;}check(failed,"Unsafe direct integrity accepted");}
struct Ops:DirectIntegrityOps {
    std::vector<unsigned char> data;unsigned calls=0,mode=0;std::uint64_t clock=1;
    std::int64_t read_at(void * target,std::size_t bytes,std::uint64_t offset)override{
        ++calls;check(bytes&&bytes<=direct_integrity_window&&bytes%direct_integrity_alignment==0&&offset%direct_integrity_alignment==0,"Direct request alignment changed");
        if(calls==2&&mode==1)return -1;
        const auto count=std::min<std::uint64_t>(bytes,data.size()-offset);
        std::memcpy(target,data.data()+offset,std::size_t(count));
        if(mode==3)clock+=2000000000ull;
        return std::int64_t(count)+(calls==2&&mode==2?-1:mode==4?1:0);
    }
    std::uint64_t now_ns()override{return clock;}
};
int main(int argc,char **argv){try{
    check(argc==3,"Supply direct-integrity fixture and independent SHA256");
    Ops prototype;std::ifstream input(argv[1],std::ios::binary);check(bool(input),"Missing fixture");
    prototype.data.assign(std::istreambuf_iterator<char>(input),{});
    std::vector<unsigned char> storage(direct_integrity_window+3*direct_integrity_alignment,0xa5);
    auto * buffer=reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(storage.data())+2*direct_integrity_alignment-1)&~std::uintptr_t(direct_integrity_alignment-1));
    sha256_t hash;sha256_init(&hash);std::size_t seen=0;
    stream_direct_integrity(prototype,buffer,prototype.data.size(),1,[&](const unsigned char *at,std::size_t count){sha256_update(&hash,at,count);seen+=count;});
    unsigned char digest[32];sha256_final(&hash,digest);std::string actual;
    for(auto value:digest){actual.push_back("0123456789abcdef"[value>>4]);actual.push_back("0123456789abcdef"[value&15]);}
    check(actual==argv[2]&&seen==prototype.data.size()&&prototype.calls==3,"Complete original bytes did not match independent SHA256");
    for(unsigned mode=1;mode<=4;++mode){Ops ops;ops.data=prototype.data;ops.mode=mode;
        rejects([&]{stream_direct_integrity(ops,buffer,ops.data.size(),1,[](const unsigned char*,std::size_t){});});
        check(ops.calls<=2,"A failed direct read was retried");}
    for(unsigned i=0;i<direct_integrity_alignment;++i)check(buffer[-int(i)-1]==0xa5&&buffer[direct_integrity_window+i]==0xa5,"Direct integrity exceeded its 1 MiB window");
    rejects([&]{stream_direct_integrity(prototype,buffer+1,1,1,[](const unsigned char*,std::size_t){});});
    std::cout<<"Independent original SHA256, aligned EOF tail, exact counts, retained failures and deadline/no-retry controls passed\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
