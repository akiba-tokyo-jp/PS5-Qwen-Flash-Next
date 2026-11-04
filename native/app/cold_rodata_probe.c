/* SPDX-License-Identifier: MIT
 * Model-independent qualification of an exclusively owned ELF address hole.
 * Synchronous CPU backing is retained until ordinary OS title close.
 */
#include "cold_rodata_probe.h"
#include "cold_rodata_manifest.h"
#include "sha256.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <unistd.h>
#include <errno.h>
extern void qwen_native_stage(const char *);
extern unsigned char qwen_cold_payload[], qwen_cold_payload_end[];
struct qwen_cold_probe_result qwen_cold_probe;
static int64_t physical = -1;
static int sample(void) {
    uint32_t free=0, minimum=0;size_t n=4,m=4;
    if(sysctlbyname("vm.stats.vm0.v_free_count",&free,&n,0,0)||n!=4||
       sysctlbyname("vm.stats.vm0.v_free_min",&minimum,&m,0,0)||m!=4||minimum!=898)return 0;
    if(!qwen_cold_probe.free_before)qwen_cold_probe.free_before=free;
    qwen_cold_probe.free_after=free;
    if(!qwen_cold_probe.minimum_free||free<qwen_cold_probe.minimum_free)qwen_cold_probe.minimum_free=free;
    return free>=minimum+21;
}
static int same(const struct stat*a,const struct stat*b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_size==b->st_size&&
        a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
        a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
__attribute__((constructor(101))) static void restore_cold_rodata(void) {
    qwen_native_stage("cold_rodata_CPU_restore_begin_GPU_not_started");
    qwen_cold_probe.status=1;
    const uintptr_t begin=(uintptr_t)qwen_cold_payload,end=(uintptr_t)qwen_cold_payload_end;
    if(!begin||begin%65536||end-begin!=COLD_BYTES||!sample())goto returned;
    qwen_cold_probe.status=2;
    void *region_begin=0,*region_end=0;uint32_t protection=0;
    /* Never replace an existing mapping. The non-fixed reservation must
     * return this exact application-owned hole before a fixed Direct map. */
    if(!sceKernelQueryMemoryProtection((void*)begin,&region_begin,&region_end,&protection))goto returned;
    void *reserved=(void*)begin;
    if(sceKernelReserveVirtualRange(&reserved,COLD_BYTES,0,65536))goto returned;
    if(reserved!=(void*)begin){(void)sceKernelMunmap(reserved,COLD_BYTES);goto returned;}
    qwen_cold_probe.status=3;
    const int64_t pool=sceKernelGetDirectMemorySize();int64_t available_start=-1;size_t available=0;
    if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&available_start,&available)||
       available_start<0||available<COLD_BYTES+(256ull<<20)||!sample())goto returned;
    if(sceKernelAllocateDirectMemory(0,pool,COLD_BYTES,65536,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)||physical<0)goto returned;
    qwen_cold_probe.allocation_retained=1;qwen_cold_probe.status=4;
    void *actual=(void*)begin;
    if(sceKernelMapDirectMemory(&actual,COLD_BYTES,3,PS5_KERNEL_MAP_FIXED,physical,16384)||actual!=(void*)begin)goto returned;
    qwen_cold_probe.mapped_bytes=COLD_BYTES;qwen_cold_probe.status=5;
    if(sceKernelQueryMemoryProtection((void*)begin,&region_begin,&region_end,&protection)||
       (uintptr_t)region_begin>begin||(uintptr_t)region_end<end||(protection&7)!=3||!sample())goto returned;
    int fd=open(COLD_PATH,O_RDONLY|O_NOFOLLOW|O_DIRECT);
    qwen_cold_probe.failure_step=1;qwen_cold_probe.source_errno=errno;
    if(fd<0)goto returned;
    qwen_cold_probe.source_flags=fcntl(fd,F_GETFL);
    struct stat before={0},after={0};int ok=qwen_cold_probe.source_flags>=0&&(qwen_cold_probe.source_flags&O_DIRECT)&&
        !fstat(fd,&before)&&S_ISREG(before.st_mode)&&before.st_nlink<=1&&
        before.st_uid<=1&&!before.st_gid&&(before.st_mode&07777)==0444&&before.st_size==COLD_BYTES&&before.st_ino;
    qwen_cold_probe.source_mode=before.st_mode;qwen_cold_probe.source_uid=before.st_uid;
    qwen_cold_probe.source_gid=before.st_gid;qwen_cold_probe.source_links=before.st_nlink;
    qwen_cold_probe.source_bytes=before.st_size;
    qwen_cold_probe.failure_step=2;qwen_cold_probe.source_errno=errno;
    struct ai_sha256 hash;ai_sha256_init(&hash);uint8_t digest[32];
    for(size_t at=0;ok&&at<COLD_BYTES;at+=65536){
        if(!sample()){ok=0;qwen_cold_probe.failure_step=3;break;}
        qwen_cold_probe.last_read=pread(fd,(void*)(begin+at),65536,(off_t)at);
        qwen_cold_probe.source_errno=errno;qwen_cold_probe.failure_step=4;
        ok=qwen_cold_probe.last_read==65536;
        if(ok){ai_sha256_update(&hash,(void*)(begin+at),65536);++qwen_cold_probe.completed_reads;}
    }
    static _Alignas(16384) unsigned char eof[16384];
    if(ok){qwen_cold_probe.last_read=pread(fd,eof,sizeof(eof),COLD_BYTES);qwen_cold_probe.failure_step=5;
        qwen_cold_probe.source_errno=errno;ok=qwen_cold_probe.last_read==0;}
    if(ok){qwen_cold_probe.failure_step=6;ok=!fstat(fd,&after)&&same(&before,&after);}
    qwen_cold_probe.source_closed=!close(fd);
    ai_sha256_final(&hash,digest);
    memcpy(qwen_cold_probe.observed_digest,digest,32);
    if(ok&&qwen_cold_probe.source_closed)qwen_cold_probe.failure_step=7;
    if(!ok||!qwen_cold_probe.source_closed||memcmp(digest,cold_digest,32))goto returned;
    qwen_cold_probe.status=6;
    if(sceKernelMprotect((void*)begin,COLD_BYTES,1)||
       sceKernelQueryMemoryProtection((void*)begin,&region_begin,&region_end,&protection)||
       (uintptr_t)region_begin>begin||(uintptr_t)region_end<end||(protection&7)!=1||!sample())goto returned;
    qwen_cold_probe.readonly=1;qwen_cold_probe.status=0;qwen_cold_probe.failure_step=0;
returned:
    qwen_native_stage("cold_rodata_CPU_restore_returned_GPU_not_started");
}
__attribute__((constructor(102))) static void check_cold_rodata_constructor(void) {
    if(qwen_cold_probe.status)return;
    uint64_t value=UINT64_C(14695981039346656037);
    const volatile unsigned char *p=qwen_cold_payload;
    for(size_t i=0;i<COLD_BYTES;++i){value^=p[i];value*=UINT64_C(1099511628211);}
    qwen_cold_probe.checksum=value;
    qwen_cold_probe.constructor_checked=value==COLD_FNV64;
    if(!qwen_cold_probe.constructor_checked)qwen_cold_probe.status=7;
    qwen_native_stage("cold_rodata_CPU_constructor_check_returned_GPU_not_started");
}
