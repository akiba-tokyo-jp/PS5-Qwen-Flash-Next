// SPDX-License-Identifier: MIT
#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "lz4.h"

// Experimental storage codec only. Original BF16 bits are reconstructed before
// use; no floating-point arithmetic, quantization or routing change is involved.
#define QWEN_BF16_MATRIX_MAX 3276800u
#define QWEN_BF16_CODEC_HEADER 32u
#define QWEN_BF16_CODEC_EXPONENT 1u
#define QWEN_BF16_CODEC_RAW 2u

static inline uint32_t qwen_codec_u32(const unsigned char *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static inline void qwen_codec_put32(unsigned char *p,uint32_t x) {
    for(unsigned i=0;i<4;++i)p[i]=(unsigned char)(x>>(8*i));
}
static inline void qwen_bf16_split(const unsigned char *raw,size_t count,
                                  unsigned char *sm,unsigned char *exponent) {
    for(size_t i=0;i<count;++i) {
        const uint16_t b=(uint16_t)raw[2*i]|((uint16_t)raw[2*i+1]<<8);
        sm[i]=(unsigned char)(((b>>8)&0x80)|(b&0x7f));
        exponent[i]=(unsigned char)(b>>7);
    }
}
static inline void qwen_bf16_join(const unsigned char *sm,const unsigned char *exponent,
                                 size_t count,unsigned char *raw) {
    for(size_t i=0;i<count;++i) {
        const uint16_t b=((uint16_t)(sm[i]&0x80)<<8)|((uint16_t)exponent[i]<<7)|(sm[i]&0x7f);
        raw[2*i]=(unsigned char)b;raw[2*i+1]=(unsigned char)(b>>8);
    }
}
static inline int qwen_codec_disjoint(const void *a,size_t na,const void *b,size_t nb) {
    const uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return x<=UINTPTR_MAX-na && y<=UINTPTR_MAX-nb && (x+na<=y || y+nb<=x);
}
struct qwen_bf16_decode_plan {
    const unsigned char *input;
    unsigned char *output,*scratch;
    uint32_t raw,codec,shards;
    size_t table;
};
// The caller separately verifies the encoded and reconstructed SHA256 digests.
// A failure never admits partially decoded bytes and never retries input.
static inline int qwen_bf16_prepare(const unsigned char *input,size_t bytes,
    unsigned char *output,size_t capacity,unsigned char *scratch,size_t scratch_bytes,
    struct qwen_bf16_decode_plan *plan) {
    if(!plan)return 0;
    if(!input||!output||bytes<QWEN_BF16_CODEC_HEADER||
       bytes>QWEN_BF16_MATRIX_MAX+QWEN_BF16_MATRIX_MAX/255u+256u||memcmp(input,"QBF16E01",8))return 0;
    const uint32_t raw=qwen_codec_u32(input+8),codec=qwen_codec_u32(input+12);
    const uint32_t shards=qwen_codec_u32(input+16),total=qwen_codec_u32(input+20);
    const uint32_t sm=qwen_codec_u32(input+24);
    if(!raw||(raw&1)||raw>QWEN_BF16_MATRIX_MAX||capacity<raw||total!=bytes||
       qwen_codec_u32(input+28)||(shards!=1&&shards!=4)||
       (codec!=QWEN_BF16_CODEC_EXPONENT&&codec!=QWEN_BF16_CODEC_RAW)||
       !qwen_codec_disjoint(input,bytes,output,raw))return 0;
    const size_t table=QWEN_BF16_CODEC_HEADER+12u*shards;
    if(table>bytes||sm>bytes-table)return 0;
    const uint32_t plain=codec==QWEN_BF16_CODEC_RAW?raw:raw/2;
    if(plain%shards || (codec==QWEN_BF16_CODEC_RAW&&(sm||shards!=1)) ||
       (codec==QWEN_BF16_CODEC_EXPONENT&&(sm!=raw/2||!scratch||scratch_bytes<plain||
        !qwen_codec_disjoint(input,bytes,scratch,plain)||!qwen_codec_disjoint(output,raw,scratch,plain))))return 0;
    size_t next=table+sm;
    for(unsigned i=0;i<shards;++i) {
        const unsigned char *entry=input+QWEN_BF16_CODEC_HEADER+12*i;
        const uint32_t offset=qwen_codec_u32(entry),packed=qwen_codec_u32(entry+4),decoded=qwen_codec_u32(entry+8);
        if(offset!=next||!packed||packed>bytes-next||decoded!=plain/shards||
           packed>(uint32_t)LZ4_compressBound((int)decoded))return 0;
        next+=packed;
    }
    if(next!=bytes)return 0;
    *plan=(struct qwen_bf16_decode_plan){input,output,scratch,raw,codec,shards,table};
    return 1;
}
// A prepared plan is immutable until every worker has returned. Each shard
// owns disjoint scratch and destination bytes, including its bit reconstruction.
static inline int qwen_bf16_decode_shard(const struct qwen_bf16_decode_plan *plan,unsigned i) {
    if(!plan||i>=plan->shards)return 0;
    const unsigned char *input=plan->input;
    const unsigned char *entry=input+QWEN_BF16_CODEC_HEADER+12*i;
    const uint32_t offset=qwen_codec_u32(entry),packed=qwen_codec_u32(entry+4),decoded=qwen_codec_u32(entry+8);
    unsigned char *target=(plan->codec==QWEN_BF16_CODEC_RAW?plan->output:plan->scratch)+(size_t)i*decoded;
    if(LZ4_decompress_safe((const char *)input+offset,(char *)target,(int)packed,(int)decoded)!=(int)decoded)return 0;
    if(plan->codec==QWEN_BF16_CODEC_EXPONENT)
        qwen_bf16_join(input+plan->table+(size_t)i*decoded,target,decoded,plan->output+2*(size_t)i*decoded);
    return 1;
}
static inline int qwen_bf16_decode(const unsigned char *input,size_t bytes,
    unsigned char *output,size_t capacity,unsigned char *scratch,size_t scratch_bytes) {
    struct qwen_bf16_decode_plan plan;
    if(!qwen_bf16_prepare(input,bytes,output,capacity,scratch,scratch_bytes,&plan))return 0;
    for(unsigned i=0;i<plan.shards;++i) {
        const unsigned char *entry=input+QWEN_BF16_CODEC_HEADER+12*i;
        const uint32_t offset=qwen_codec_u32(entry),packed=qwen_codec_u32(entry+4),decoded=qwen_codec_u32(entry+8);
        unsigned char *target=(plan.codec==QWEN_BF16_CODEC_RAW?output:scratch)+(size_t)i*decoded;
        if(LZ4_decompress_safe((const char *)input+offset,(char *)target,(int)packed,(int)decoded)!=(int)decoded)return 0;
    }
    if(plan.codec==QWEN_BF16_CODEC_EXPONENT)qwen_bf16_join(input+plan.table,scratch,plan.raw/2,output);
    return 1;
}
