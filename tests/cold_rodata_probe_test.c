/* SPDX-License-Identifier: MIT
 * Fault injection over the actual restorer body; no OS mappings are changed.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "cold_rodata_probe.h"
#include "cold_rodata_manifest.h"
typedef long long ssize_t;
struct timestamp {long tv_sec,tv_nsec;};
struct stat {uint64_t st_dev,st_ino,st_size,st_mode,st_uid,st_gid,st_nlink;struct timestamp st_mtim,st_ctim;};
#define S_ISREG(v) (((v)&0170000)==0100000)
#define O_RDONLY 0
#define O_NOFOLLOW 1
#define O_DIRECT 2
#define F_GETFL 3
#define PS5_KERNEL_DIRECT_TYPE_CPU 12
#define PS5_KERNEL_MAP_FIXED 0x10
static unsigned char *qwen_cold_payload;
#define qwen_cold_payload_end (qwen_cold_payload+COLD_BYTES)
enum {GOOD,LOW,EXISTING,RESERVE_FAIL,RESERVE_ELSEWHERE,POOL,AVAILABLE,ALLOCATE,MAP,
      WRITABLE,OPEN,IDENTITY,SHORT_READ,CHANGED,HASH,CLOSE,PROTECT,READONLY,TITLE_VIEW,FLAGS,FAULTS};
static int fault,queries,allocations,maps,reservations,unmaps,opens,closes,reads,stages;
#define CHECK(c) do{if(!(c)){fprintf(stderr,"line=%d fault=%d\n",__LINE__,fault);exit(1);}}while(0)
static void qwen_native_stage(const char*p){CHECK(p&&*p);++stages;}
static int sysctlbyname(const char*n,void*out,size_t*bytes,const void*a,size_t b){
    CHECK(!a&&!b&&*bytes==4);*(uint32_t*)out=strstr(n,"free_min")?898:(fault==LOW?900:2500);return 0;
}
static int sceKernelQueryMemoryProtection(void*p,void**begin,void**end,uint32_t*protection){
    CHECK(p==qwen_cold_payload);++queries;
    if(queries==1&&fault!=EXISTING)return -1;
    *begin=qwen_cold_payload;*end=qwen_cold_payload+COLD_BYTES;
    *protection=queries==2?(fault==WRITABLE?7:3):(fault==READONLY?3:1);return 0;
}
static int sceKernelReserveVirtualRange(void**p,size_t n,int flags,size_t alignment){
    CHECK(*p==qwen_cold_payload&&n==COLD_BYTES&&!flags&&alignment==65536);++reservations;
    if(fault==RESERVE_ELSEWHERE)*p=qwen_cold_payload+65536;
    return fault==RESERVE_FAIL?-1:0;
}
static int sceKernelMunmap(void*p,size_t n){CHECK(p==qwen_cold_payload+65536&&n==COLD_BYTES);++unmaps;return 0;}
static int64_t sceKernelGetDirectMemorySize(void){return fault==POOL?-1:1ll<<32;}
static int sceKernelAvailableDirectMemorySize(int64_t a,int64_t b,size_t align,int64_t*start,size_t*n){
    CHECK(!a&&b==(1ll<<32)&&align==65536);*start=0;*n=fault==AVAILABLE?COLD_BYTES:1u<<30;return 0;
}
static int sceKernelAllocateDirectMemory(int64_t a,int64_t b,size_t n,size_t align,int type,int64_t*p){
    CHECK(!a&&b==(1ll<<32)&&n==COLD_BYTES&&align==65536&&type==12);++allocations;*p=65536;return fault==ALLOCATE?-1:0;
}
static int sceKernelMapDirectMemory(void**p,size_t n,int prot,int flags,int64_t phys,size_t align){
    CHECK(*p==qwen_cold_payload&&n==COLD_BYTES&&prot==3&&flags==0x10&&phys==65536&&align==16384);++maps;return fault==MAP?-1:0;
}
static int open(const char*p,int flags){CHECK(!strcmp(p,COLD_PATH)&&flags==3);++opens;return fault==OPEN?-1:3;}
static int fcntl(int fd,int command){CHECK(fd==3&&command==F_GETFL);return fault==FLAGS?0:O_DIRECT;}
static int fstat(int fd,struct stat*s){
    CHECK(fd==3);memset(s,0,sizeof(*s));s->st_dev=1;s->st_ino=2;s->st_size=COLD_BYTES;
    s->st_mode=0100444;s->st_uid=1;s->st_nlink=1;
    if(fault==TITLE_VIEW){s->st_uid=0;s->st_nlink=0;}
    if(fault==IDENTITY)s->st_mode=0100644;
    if(fault==CHANGED&&reads)s->st_ino=3;
    return 0;
}
static ssize_t pread(int fd,void*p,size_t n,off_t at){
    CHECK(fd==3);++reads;if(at==COLD_BYTES){CHECK(n==16384);return 0;}
    CHECK(n==65536&&at>=0&&(uint64_t)at<COLD_BYTES&&p==qwen_cold_payload+at);
    for(size_t i=0;i<n;++i)((unsigned char*)p)[i]=(unsigned char)(at+i);
    if(fault==HASH)((unsigned char*)p)[0]^=1;
    return fault==SHORT_READ?(ssize_t)n-1:(ssize_t)n;
}
static int close(int fd){CHECK(fd==3);++closes;return fault==CLOSE?-1:0;}
static int sceKernelMprotect(void*p,size_t n,int prot){CHECK(p==qwen_cold_payload&&n==COLD_BYTES&&prot==1);return fault==PROTECT?-1:0;}
#include "cold_rodata_under_test.h"
int main(void){
    void*storage=malloc(COLD_BYTES+65536);CHECK(storage);
    qwen_cold_payload=(unsigned char*)(((uintptr_t)storage+65535)&~(uintptr_t)65535);
    for(fault=GOOD;fault<FAULTS;++fault){
        memset(&qwen_cold_probe,0,sizeof(qwen_cold_probe));
        queries=allocations=maps=reservations=unmaps=opens=closes=reads=stages=0;
        restore_cold_rodata();check_cold_rodata_constructor();
        CHECK(stages>=2&&allocations<=1&&maps<=1&&reservations<=1&&opens<=1&&closes<=1);
        if(fault==GOOD||fault==TITLE_VIEW){CHECK(!qwen_cold_probe.status&&qwen_cold_probe.source_closed&&qwen_cold_probe.readonly&&
            qwen_cold_probe.constructor_checked&&qwen_cold_probe.checksum==COLD_FNV64&&reads==129);}
        else CHECK(qwen_cold_probe.status&&!qwen_cold_probe.constructor_checked);
        if(fault==LOW||fault==EXISTING)CHECK(!reservations&&!allocations&&!maps&&!opens);
        if(fault==RESERVE_ELSEWHERE)CHECK(unmaps==1&&!allocations&&!maps);
        if(fault>=IDENTITY)CHECK(closes==1);
    }
    printf("cold_rodata_actual_body_controls=%d positive=2 negative=%d OS_operations=0\n",FAULTS,FAULTS-2);
    free(storage);
    return 0;
}
