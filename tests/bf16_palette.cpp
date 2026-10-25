// SPDX-License-Identifier: MIT
#include "bf16_palette.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <vector>
namespace {
unsigned checks=0;
void require(bool ok){++checks;if(!ok)throw std::runtime_error("Exact palette control failed");}
void roundtrip(const std::vector<unsigned char>&raw) {
    const auto bound=qwen_palette_bound(raw.size()/2);
    std::vector<unsigned char> encoded(bound+64,0xa7),restored(raw.size()+64,0xb9);
    const auto n=qwen_palette_encode(raw.data(),raw.size(),encoded.data(),bound);
    require(n>0&&n<=bound);require(qwen_palette_decode(encoded.data(),n,restored.data(),raw.size()));
    require(std::equal(raw.begin(),raw.end(),restored.begin()));
    require(std::all_of(restored.begin()+raw.size(),restored.end(),[](auto b){return b==0xb9;}));
    require(std::all_of(encoded.begin()+bound,encoded.end(),[](auto b){return b==0xa7;}));
    for(unsigned field: {0u,4u,8u,12u,16u,20u,24u,28u,32u,36u,40u,44u,55u}) {
        auto damaged=encoded;damaged[field]^=0x80;
        std::fill(restored.begin(),restored.end(),0xb9);
        require(!qwen_palette_decode(damaged.data(),n,restored.data(),raw.size()));
        require(std::all_of(restored.begin(),restored.end(),[](auto b){return b==0xb9;}));
    }
    require(!qwen_palette_decode(encoded.data(),n-1,restored.data(),raw.size()));
    require(!qwen_palette_decode(encoded.data(),n,encoded.data()+64,raw.size()));
    require(!qwen_palette_encode(raw.data(),raw.size(),encoded.data(),bound-1));
    const auto prefix=qwen_palette_u32(encoded.data()+24);
    encoded[prefix+4]^=1;
    require(!qwen_palette_decode(encoded.data(),n,restored.data(),raw.size()));
}
}
int main(int argc,char **argv)try {
    if(argc==4) {
        std::ifstream file(argv[1],std::ios::binary);
        std::vector<unsigned char> raw((std::istreambuf_iterator<char>(file)),{});
        require(raw.size()==3276800);roundtrip(raw);
        std::vector<unsigned char> encoded(qwen_palette_bound(raw.size()/2));
        const auto n=qwen_palette_encode(raw.data(),raw.size(),encoded.data(),encoded.size());
        std::ofstream out(argv[2],std::ios::binary);out.write((const char *)encoded.data(),n);out.close();require(bool(out));
        std::ofstream original(argv[3],std::ios::binary);original.write((const char *)raw.data(),raw.size());original.close();require(bool(original));
        std::printf("{\"raw_bytes\":%zu,\"encoded_bytes\":%zu,\"exact\":true,\"checks\":%u}\n",raw.size(),n,checks);
        return 0;
    }
    require(argc==1);require(qwen_palette_bound(0)==0);require(qwen_palette_bound(65)==0);
    require(qwen_palette_bound(QWEN_PALETTE_MAX_VALUES+64)==0);
    std::vector<unsigned char> patterns(65536*2);
    for(unsigned i=0;i<65536;++i){patterns[2*i]=(unsigned char)i;patterns[2*i+1]=(unsigned char)(i>>8);}
    roundtrip(patterns);
    std::vector<unsigned char> raw(3276800);uint32_t state=174615u;
    for(unsigned repeat=0;repeat<4;++repeat) {
        for(auto &b:raw){state=state*1664525u+1013904223u;b=(unsigned char)(state>>24);}
        roundtrip(raw);
    }
    for(auto &b:raw)b=0;roundtrip(raw);
    raw.resize(128);roundtrip(raw);
    std::printf("{\"all_65536_BF16_patterns_exact\":true,\"maximum_size_roundtrips\":5,\"checks\":%u}\n",checks);
    return 0;
}catch(const std::exception &e){std::fprintf(stderr,"%s\n",e.what());return 1;}
