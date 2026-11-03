/* SPDX-License-Identifier: MIT
 * Fault-inject the actual early mapper without any host OS mapping calls.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include "early_CPU_tables_manifest.h"
static unsigned char*memory;
#define __qwen_driver_tables_start memory
#define __qwen_driver_tables_end (memory+EARLY_ORIGINAL_TABLE_BYTES)
#define __qwen_early_tables_end (memory+EARLY_DIRECT_BYTES)
#define PS5_KERNEL_DIRECT_TYPE_CPU 12
#define PS5_KERNEL_MAP_FIXED 0x10
enum {GOOD,SHAPE,PLAN,TARGET,OVERLAP,SUM,LOW,EXISTING,RESERVE,ELSEWHERE,POOL,AVAILABLE,ALLOCATE,MAP,PROTECTION,ZERO_HASH,FNV,FAULTS};
static int fault,queries,allocations,maps,unmaps,stages,parks;static jmp_buf parked;
#define CHECK(x) do{if(!(x)){fprintf(stderr,"fault=%d line=%d\n",fault,__LINE__);exit(1);}}while(0)
static void qwen_native_stage(const char*line){CHECK(line&&*line);++stages;}
static void qwen_native_halt(const char*line){CHECK(strstr(line,"returned_failure"));++parks;longjmp(parked,1);}
static int sysctlbyname(const char*name,void*out,size_t*n,const void*a,size_t b){
    CHECK(*n==4&&!a&&!b);*(uint32_t*)out=strstr(name,"free_min")?898:(fault==LOW?900:3000);return 0;
}
static int sceKernelQueryMemoryProtection(void*p,void**begin,void**end,uint32_t*protection){
    CHECK(p==memory);++queries;if(queries==1&&fault!=EXISTING)return -1;
    *begin=memory;*end=memory+EARLY_DIRECT_BYTES;*protection=fault==PROTECTION?7:3;return 0;
}
static int sceKernelReserveVirtualRange(void**p,size_t n,int flags,size_t align){
    CHECK(*p==memory&&n==EARLY_DIRECT_BYTES&&!flags&&align==65536);
    if(fault==ELSEWHERE)*p=memory+65536;return fault==RESERVE?-1:0;
}
static int sceKernelMunmap(void*p,size_t n){CHECK(p==memory+65536&&n==EARLY_DIRECT_BYTES);++unmaps;return 0;}
static int64_t sceKernelGetDirectMemorySize(void){return fault==POOL?-1:(1ll<<32);}
static int sceKernelAvailableDirectMemorySize(int64_t low,int64_t high,size_t align,int64_t*start,size_t*available){
    CHECK(!low&&high==(1ll<<32)&&align==65536);*start=0;*available=fault==AVAILABLE?EARLY_DIRECT_BYTES:(1u<<30);return 0;
}
static int sceKernelAllocateDirectMemory(int64_t low,int64_t high,size_t n,size_t align,int type,int64_t*physical){
    CHECK(!low&&high==(1ll<<32)&&n==EARLY_DIRECT_BYTES&&align==65536&&type==12);++allocations;*physical=65536;return fault==ALLOCATE?-1:0;
}
static int sceKernelMapDirectMemory(void**p,size_t n,int protection,int flags,int64_t physical,size_t align){
    CHECK(*p==memory&&n==EARLY_DIRECT_BYTES&&protection==3&&flags==0x10&&physical==65536&&align==16384);++maps;return fault==MAP?-1:0;
}
static void*test_memset(void*p,int value,size_t n){
    void*result=memset(p,value,n);if(fault==ZERO_HASH&&n==EARLY_DIRECT_BYTES)((unsigned char*)p)[n-1]^=1;return result;
}
#define memset test_memset
#include "early_CPU_tables_under_test.h"
#undef memset
int main(void){
    void*storage=malloc(EARLY_DIRECT_BYTES+131072);CHECK(storage);
    unsigned char*aligned=(unsigned char*)(((uintptr_t)storage+65535)&~(uintptr_t)65535);
    static struct original_table tables[673];static const unsigned char packed=1;
    for(fault=GOOD;fault<FAULTS;++fault){
        memory=aligned+(fault==SHAPE?16384:0);memset(&result,0,sizeof(result));result.physical=-1;
        queries=allocations=maps=unmaps=stages=parks=0;
        uint64_t used=0;for(unsigned i=0;i<673;++i){
            tables[i].target=memory+used;tables[i].bytes=9471408/673+(i<9471408%673);used+=tables[i].bytes;}
        qwen_driver_table_storage=(struct original_plan){tables,673,&packed,EARLY_PACKED_BYTES,memory,memory+EARLY_ORIGINAL_TABLE_BYTES};
        if(fault==PLAN)--qwen_driver_table_storage.count;
        if(fault==TARGET)tables[672].target=memory+EARLY_ORIGINAL_TABLE_BYTES;
        if(fault==OVERLAP)tables[1].target=tables[0].target;
        if(fault==SUM)--tables[672].bytes;
        if(!setjmp(parked)){
            early_CPU_tables_map();if(fault==FNV)memory[0]^=1;early_CPU_tables_check();
        }
        CHECK(result.all_CPU_operations_returned&&allocations<=1&&maps<=1);
        if(fault==GOOD)CHECK(!result.status&&!parks&&result.zeroed&&result.checksum_passed&&result.checksum==EARLY_ZERO_FNV64);
        else CHECK(result.status&&parks==1&&!result.checksum_passed);
        if(fault<=LOW&&fault!=GOOD)CHECK(!allocations&&!maps);
        if(fault==ELSEWHERE)CHECK(unmaps==1&&!allocations&&!maps);
    }
    free(storage);printf("early_CPU_actual_body_controls=%d positive=1 refusals=%d OS_mapping_calls=0 GPU_calls=0\n",FAULTS,FAULTS-1);return 0;
}
