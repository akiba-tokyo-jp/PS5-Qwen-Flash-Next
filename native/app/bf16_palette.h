// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>

// Experimental exact storage encoding. No floating-point value is rounded.
// Each independent tile stores 64 sign/mantissa bytes, three exponent-code
// bitmaps and an indexed stream of verbatim uncommon exponents.
#define QWEN_PALETTE_HEADER 64u
#define QWEN_PALETTE_MAX_VALUES 1638400u
#define QWEN_PALETTE_MAGIC UINT32_C(0x314c5042)
static inline uint32_t qwen_palette_u32(const unsigned char *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static inline void qwen_palette_put32(unsigned char *p,uint32_t x) {
    for(unsigned i=0;i<4;++i)p[i]=(unsigned char)(x>>(8*i));
}
static inline unsigned qwen_palette_popcount(uint32_t x) {
    x=x-((x>>1)&UINT32_C(0x55555555));
    x=(x&UINT32_C(0x33333333))+((x>>2)&UINT32_C(0x33333333));
    return (unsigned)((((x+(x>>4))&UINT32_C(0x0f0f0f0f))*UINT32_C(0x01010101))>>24);
}
static inline int qwen_palette_overlap(const void *a,size_t na,const void *b,size_t nb) {
    const uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return !a||!b||na>UINTPTR_MAX-x||nb>UINTPTR_MAX-y||(x<y+nb&&y<x+na);
}
static inline size_t qwen_palette_bound(size_t values) {
    if(!values||values>QWEN_PALETTE_MAX_VALUES||values%64)return 0;
    return QWEN_PALETTE_HEADER+values+values*3/8+(values/64+1)*4+values;
}
static inline size_t qwen_palette_encode(const unsigned char *raw,size_t raw_bytes,
    unsigned char *encoded,size_t capacity) {
    if(raw_bytes%128)return 0;
    const size_t n=raw_bytes/2,bound=qwen_palette_bound(n);
    if(!bound||capacity<bound||qwen_palette_overlap(raw,raw_bytes,encoded,capacity))return 0;
    uint32_t histogram[256]={0};unsigned char codes[256]={0},palette[7];
    for(size_t i=0;i<n;++i)++histogram[(raw[2*i]>>7)|((unsigned)(raw[2*i+1]&127)<<1)];
    for(unsigned i=0;i<7;++i) {
        unsigned best=256;
        for(unsigned e=0;e<256;++e)if(!codes[e]&&(best==256||histogram[e]>histogram[best]))best=e;
        palette[i]=(unsigned char)best;codes[best]=(unsigned char)(i+1);
    }
    const uint32_t tiles=(uint32_t)(n/64),sm=64,maps=sm+(uint32_t)n;
    const uint32_t prefix=maps+tiles*24,escapes=prefix+(tiles+1)*4;
    memset(encoded,0,escapes);
    qwen_palette_put32(encoded,QWEN_PALETTE_MAGIC);qwen_palette_put32(encoded+4,(uint32_t)n);
    qwen_palette_put32(encoded+8,(uint32_t)raw_bytes);qwen_palette_put32(encoded+12,tiles);
    qwen_palette_put32(encoded+16,sm);qwen_palette_put32(encoded+20,maps);
    qwen_palette_put32(encoded+24,prefix);qwen_palette_put32(encoded+28,escapes);
    qwen_palette_put32(encoded+40,64);qwen_palette_put32(encoded+44,1);
    memcpy(encoded+48,palette,7);
    uint32_t count=0;
    for(uint32_t tile=0;tile<tiles;++tile) {
        uint32_t planes[6]={0};qwen_palette_put32(encoded+prefix+tile*4,count);
        for(unsigned j=0;j<64;++j) {
            const size_t i=(size_t)tile*64+j;
            const unsigned char exp=(unsigned char)((raw[2*i]>>7)|((raw[2*i+1]&127)<<1));
            const unsigned code=codes[exp];
            encoded[sm+i]=(unsigned char)((raw[2*i+1]&128)|(raw[2*i]&127));
            for(unsigned bit=0;bit<3;++bit)if(code&(1u<<bit))planes[bit*2+j/32]|=UINT32_C(1)<<(j%32);
            if(!code)encoded[escapes+count++]=exp;
        }
        for(unsigned k=0;k<6;++k)qwen_palette_put32(encoded+maps+tile*24+k*4,planes[k]);
    }
    qwen_palette_put32(encoded+prefix+tiles*4,count);
    qwen_palette_put32(encoded+32,count);qwen_palette_put32(encoded+36,escapes+count);
    return escapes+count;
}
typedef struct qwen_palette_plan {
    const unsigned char *encoded;
    unsigned char *output;
    uint32_t values,tiles,sm,maps,prefix,escapes,encoded_bytes;
} qwen_palette_plan;
static inline int qwen_palette_prepare(const unsigned char *encoded,size_t bytes,
    unsigned char *output,size_t raw_bytes,qwen_palette_plan *plan) {
    if(!encoded||bytes<64||!plan||raw_bytes%128||!qwen_palette_bound(raw_bytes/2)||
       qwen_palette_overlap(encoded,bytes,output,raw_bytes)||qwen_palette_u32(encoded)!=QWEN_PALETTE_MAGIC)return 0;
    const uint32_t n=qwen_palette_u32(encoded+4),tiles=qwen_palette_u32(encoded+12);
    if(n!=raw_bytes/2||qwen_palette_u32(encoded+8)!=raw_bytes||tiles!=n/64||
       qwen_palette_u32(encoded+40)!=64||qwen_palette_u32(encoded+44)!=1)return 0;
    const uint32_t sm=64,maps=sm+n,prefix=maps+tiles*24,escapes=prefix+(tiles+1)*4;
    if(qwen_palette_u32(encoded+16)!=sm||qwen_palette_u32(encoded+20)!=maps||
       qwen_palette_u32(encoded+24)!=prefix||qwen_palette_u32(encoded+28)!=escapes||
       escapes>bytes||qwen_palette_u32(encoded+32)>n||
       qwen_palette_u32(encoded+36)!=bytes||bytes!=(size_t)escapes+qwen_palette_u32(encoded+32))return 0;
    for(unsigned i=55;i<64;++i)if(encoded[i])return 0;
    for(unsigned i=0;i<7;++i)for(unsigned j=0;j<i;++j)if(encoded[48+i]==encoded[48+j])return 0;
    uint32_t previous=0;
    for(uint32_t tile=0;tile<tiles;++tile) {
        if(qwen_palette_u32(encoded+prefix+tile*4)!=previous)return 0;
        unsigned uncommon=0;
        for(unsigned half=0;half<2;++half) {
            const unsigned char *p=encoded+maps+tile*24+half*4;
            const uint32_t common=qwen_palette_u32(p)|qwen_palette_u32(p+8)|qwen_palette_u32(p+16);
            uncommon+=32-qwen_palette_popcount(common);
        }
        if(uncommon>qwen_palette_u32(encoded+32)-previous)return 0;
        previous+=uncommon;
    }
    if(qwen_palette_u32(encoded+prefix+tiles*4)!=previous||previous!=qwen_palette_u32(encoded+32))return 0;
    *plan=(qwen_palette_plan){encoded,output,n,tiles,sm,maps,prefix,escapes,(uint32_t)bytes};return 1;
}
static inline void qwen_palette_decode_tiles(const qwen_palette_plan *p,uint32_t first,uint32_t count) {
    for(uint32_t tile=first;tile<first+count;++tile) {
        uint32_t next=qwen_palette_u32(p->encoded+p->prefix+tile*4),planes[6];
        for(unsigned k=0;k<6;++k)planes[k]=qwen_palette_u32(p->encoded+p->maps+tile*24+k*4);
        for(unsigned j=0;j<64;++j) {
            const unsigned half=j/32,shift=j%32;
            const unsigned code=((planes[half]>>shift)&1)|(((planes[2+half]>>shift)&1)<<1)|(((planes[4+half]>>shift)&1)<<2);
            const unsigned char exponent=code?p->encoded[47+code]:p->encoded[p->escapes+next++];
            const size_t i=(size_t)tile*64+j;const unsigned char sm=p->encoded[p->sm+i];
            p->output[2*i]=(unsigned char)((sm&127)|(exponent<<7));
            p->output[2*i+1]=(unsigned char)((sm&128)|(exponent>>1));
        }
    }
}
static inline int qwen_palette_decode(const unsigned char *encoded,size_t bytes,
    unsigned char *output,size_t raw_bytes) {
    qwen_palette_plan plan;
    if(!qwen_palette_prepare(encoded,bytes,output,raw_bytes,&plan))return 0;
    qwen_palette_decode_tiles(&plan,0,plan.tiles);return 1;
}
