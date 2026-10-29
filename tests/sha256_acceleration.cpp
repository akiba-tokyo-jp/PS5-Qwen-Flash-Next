// SPDX-License-Identifier: MIT
#include <algorithm>
#include <cstddef>
#include <cstdint>
extern "C" {
#include "hash/sha256/sha256.h"
void qwen_sha256_scalar_update(sha256_t*,const unsigned char*,std::size_t);
__declspec(dllexport) void qwen_sha256_test(unsigned char*out,const unsigned char*data,std::size_t bytes,std::size_t chunk,int scalar){
    sha256_t hash;sha256_init(&hash);
    while(bytes){const auto n=std::min(chunk,bytes);(scalar?qwen_sha256_scalar_update:sha256_update)(&hash,data,n);data+=n;bytes-=n;}
    sha256_final(&hash,out);
}
}
