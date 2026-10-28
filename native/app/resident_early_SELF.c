/* SPDX-License-Identifier: MIT
 * One pure-C whole SELF read before C++ initializers. No GPU or model work.
 * Expected SHA is bound to the verified launch receipt later, before GPU work.
 */
#include "resident_early_SELF.h"
#include <ps5platform/kernel.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <time.h>
#include "hash/sha256/sha256.h"
extern void qwen_native_stage(const char *);
enum { WINDOW=65536, MAX_SELF=32<<20 };
static struct qwen_resident_early_SELF result;
static int attempted;
static uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;}
static int scalar(const char *name,uint32_t *value){
    struct {uint64_t a;uint32_t value;uint64_t b;} s={UINT64_C(0x639be51948c7a2d0),0,UINT64_C(0x639be51948c7a2d0)};
    size_t bytes=4;if(sysctlbyname(name,&s.value,&bytes,NULL,0)||bytes!=4||s.a!=UINT64_C(0x639be51948c7a2d0)||s.b!=s.a)return 0;*value=s.value;return 1;
}
static int sample(void){
    uint32_t free=0,minimum=0,reserved=0,target=0;
    if(!scalar("vm.stats.vm0.v_free_count",&free)||!scalar("vm.stats.vm0.v_free_min",&minimum)||
       !scalar("vm.stats.vm0.v_free_reserved",&reserved)||!scalar("vm.stats.vm0.v_free_target",&target)||
       !reserved||reserved>minimum||minimum>=target||minimum>UINT32_MAX-21)return 0;
    /* This narrow CPU recovery scope retains the OS low-free threshold plus
     * 17 sampled Direct metadata pages, 2 sampled idle pages and 2 selected
     * extra pages. It is not a universal bound or GPU/ordinary admission.
     * Reserved is recorded separately; it is not added to the low-free mark.
     */
    result.minimum=minimum;result.reserved=reserved;result.selected_floor=minimum+21;
    if(!result.free_before)result.free_before=free;
    if(!result.minimum_free||free<result.minimum_free)result.minimum_free=free;
    result.free_after=free;return free>=result.selected_floor;
}
static int identity(int fd,uint64_t out[10]){
    struct stat s;if(fstat(fd,&s)||!S_ISREG(s.st_mode)||s.st_size<=0||s.st_size>MAX_SELF||!s.st_ino)return 0;
    const uint64_t values[10]={(uint64_t)s.st_dev,(uint64_t)s.st_ino,(uint64_t)s.st_mode,(uint64_t)s.st_uid,(uint64_t)s.st_gid,
        (uint64_t)s.st_size,(uint64_t)s.st_mtim.tv_sec,(uint64_t)s.st_mtim.tv_nsec,(uint64_t)s.st_ctim.tv_sec,(uint64_t)s.st_ctim.tv_nsec};
    memcpy(out,values,sizeof(values));return 1;
}
const struct qwen_resident_early_SELF *qwen_resident_early_SELF_result(void){return &result;}
int qwen_resident_hash_SELF_before_CXX(void){
    if(attempted++)return 0;
    qwen_native_stage("early_SELF_CPU_read_scope_before_CXX GPU_calls=0 window_bytes=65536 ordinary_GPU_floor_unchanged=1");
    const uint64_t start=now();if(!start||!sample())return 0;
    const int64_t pool=sceKernelGetDirectMemorySize();int64_t available_start=-1,physical=-1;size_t available=0;
    if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&available_start,&available)||available_start<0||available<WINDOW+(256ull<<20))return 0;
    int fd=open("/app0/eboot.bin",O_RDONLY|O_NOFOLLOW|O_DIRECT);if(fd<0)return 0;
    if(!identity(fd,result.identity)||(fcntl(fd,F_GETFL)&O_DIRECT)!=O_DIRECT)return 0;result.Direct_flag_verified=1;result.bytes=result.identity[5];
    if(sceKernelAllocateDirectMemory(0,pool,WINDOW,65536,PS5_KERNEL_DIRECT_TYPE_CPU,&physical)||physical<0)return 0;
    void *buffer=NULL;if(sceKernelMapDirectMemory(&buffer,WINDOW,3,0,physical,65536)||!buffer||(uintptr_t)buffer%65536)return 0;
    sha256_t hash;sha256_init(&hash);uint64_t offset=0;
    while(offset<result.bytes){
        if(!sample()||!now()||now()-start>UINT64_C(30000000000))return 0;
        qwen_native_stage("early_SELF_Direct_read_before_native_call GPU_calls=0");
        const ssize_t got=pread(fd,buffer,WINDOW,(off_t)offset);++result.read_calls;
        qwen_native_stage("early_SELF_Direct_read_returned GPU_calls=0");
        const size_t expected=result.bytes-offset<WINDOW?(size_t)(result.bytes-offset):WINDOW;
        if(got!=(ssize_t)expected)return 0;sha256_update(&hash,buffer,expected);offset+=expected;
    }
    qwen_native_stage("early_SELF_Direct_EOF_before_native_call GPU_calls=0");
    const ssize_t eof=pread(fd,buffer,WINDOW,(off_t)((result.bytes+WINDOW-1)&~(uint64_t)(WINDOW-1)));++result.read_calls;
    qwen_native_stage("early_SELF_Direct_EOF_returned GPU_calls=0");
    uint64_t after[10];if(eof||!identity(fd,after)||memcmp(after,result.identity,sizeof(after)))return 0;
    const int named=open("/app0/eboot.bin",O_RDONLY|O_NOFOLLOW);if(named<0||!identity(named,after)||memcmp(after,result.identity,sizeof(after))||close(named))return 0;
    sha256_final(&hash,result.sha256);
    if(close(fd)||sceKernelMunmap(buffer,WINDOW)||sceKernelReleaseDirectMemory(physical,WINDOW)||!sample())return 0;
    result.elapsed_ns=now()-start;result.completed=1;
    qwen_native_stage("early_SELF_whole_Direct_hash_completed_before_CXX expected_binding_pending_GPU_not_started=1");return 1;
}
