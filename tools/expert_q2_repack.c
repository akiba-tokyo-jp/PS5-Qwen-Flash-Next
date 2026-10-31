// SPDX-License-Identifier: MIT
// Q2_K decoding follows ggml at0a1ef309cdbb9f2024f58a38fb4c42352c5db569.
// Preserve the upstream MIT notices in native/qwen_flash_next.
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#if defined(_WIN32)
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
// Convert the current Q2_K payload through F32, without a BF16 intermediate.
EXPORT int qwen_repack_q2k_q20(const uint8_t*input,uint8_t*output,size_t blocks){
    if(!input||!output||!blocks)return 1;
    for(size_t b=0;b<blocks;++b){
        const uint8_t*p=input+b*84;_Float16 dh,mh;memcpy(&dh,p+80,2);memcpy(&mh,p+82,2);
        const float d=(float)dh,m=(float)mh;if(!__builtin_isfinite(d)||!__builtin_isfinite(m))return 2;
        float values[256];unsigned at=0,is=0;const uint8_t*q=p+16;
        for(unsigned n=0;n<256;n+=128){
            for(unsigned shift=0;shift<8;shift+=2){
                uint8_t sc=p[is++];float dl=d*(sc&15),ml=m*(sc>>4);
                for(unsigned l=0;l<16;++l)values[at++]=dl*((q[l]>>shift)&3)-ml;
                sc=p[is++];dl=d*(sc&15);ml=m*(sc>>4);
                for(unsigned l=0;l<16;++l)values[at++]=dl*((q[l+16]>>shift)&3)-ml;
            }
            q+=32;
        }
        for(unsigned sub=0;sub<4;++sub){
            const float*x=values+sub*64;float scale=0;
            for(unsigned i=0;i<64;++i){if(!__builtin_isfinite(x[i]))return 2;if(fabsf(x[i])>scale)scale=fabsf(x[i]);}
            const _Float16 half=(_Float16)scale;if(!__builtin_isfinite((float)half))return 3;
            const float inverse=scale?1.0f/scale:0;if(!__builtin_isfinite(inverse))return 4;
            uint8_t*dst=output+b*72+sub*18;memcpy(dst,&half,2);memset(dst+2,0,16);
            for(unsigned i=0;i<64;++i){int code=(int)roundf(x[i]*inverse)+1;
                if(code<0)code=0;if(code>3)code=3;dst[2+i/4]|=(uint8_t)(code<<(2*(i%4)));}
        }
    }
    return 0;
}
