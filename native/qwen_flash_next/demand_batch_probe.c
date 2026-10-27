/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded CPU-only comparison of pair waves and completion-driven delivery.
 */
#include "qualified_context_guard.c"
#include "direct_vm_policy.h"
#include "completion_probe_context.h"
#include "completion_probe_io.h"
#include "bf16_lossless.h"
#include "hash/sha256/sha256.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#define IO_BYTES 0u
#define DESTINATION_STRIDE 3293184u
#define DESTINATION_BYTES COMPLETION_DESTINATION_BYTES
#define WINDOW (IO_BYTES+DESTINATION_BYTES)
#define ALIGNMENT 16384u
_Static_assert(COMPLETION_SAMPLES*DESTINATION_STRIDE<=DESTINATION_BYTES,"Separate destination budget");
static int pending,pool_started,pool_stopped;
uint64_t completion_probe_now(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static int headroom(unsigned additional_pages) {
    uint32_t a=0,b=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&a,&minimum,&reserved,&page,&b};
    for(unsigned i=0;i<5;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    const uint64_t required=(uint64_t)minimum+(reserved>256?reserved:256)+additional_pages;
    const int rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    if(additional_pages&&!report("PREALLOC_HEADROOM free_first=%u free_last=%u minimum=%u reserved=%u additional_pages=%u required=%llu flexible_bytes=%zu rc=%d",a,b,minimum,reserved,additional_pages,(unsigned long long)required,flexible,rc))return 0;
    return page==ALIGNMENT&&minimum&&reserved&&reserved<=minimum&&required<=UINT32_MAX&&
        a>=required&&b>=required&&!rc&&flexible>=(264u<<20);
}
int completion_probe_permit(void){return headroom(0);}
int completion_probe_event(unsigned returned,unsigned slot,uint64_t id,uint64_t offset,uint64_t bytes,
    int64_t result,uint64_t started,uint64_t finished) {
    return report("IO_%s slot=%u id=%llu offset=%llu bytes=%llu result=%lld start_ns=%llu end_ns=%llu",
        returned?"RETURNED":"BEFORE",slot,(unsigned long long)id,(unsigned long long)offset,
        (unsigned long long)bytes,(long long)result,(unsigned long long)started,(unsigned long long)finished);
}
static void retain(void) {
    (void)report("RETAIN source_backing=1 no_retry=1 GPU_calls=0");for(;;)usleep(1000000);
}
static int unchanged(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&
        a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&
        a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int digest(const void *data,size_t bytes,const unsigned char expected[32]) {
    sha256_t h;unsigned char result[32];sha256_init(&h);sha256_update(&h,data,bytes);sha256_final(&h,result);
    return !memcmp(result,expected,32);
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,mapped=0,fd=-1,initial_valid=0,rc=0;int64_t physical=-1;unsigned char *window=NULL;
    struct stat initial={0},current={0};
    output_fd=open(COMPLETION_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s io_bytes=%u destination_bytes=%u total_Direct_bytes=%u samples=%u groups=%u modes=%u rounds=%u maximum_outstanding_reads=2 GPU_calls=0 title_launches=0",CLOSE_NONCE,IO_BYTES,DESTINATION_BYTES,WINDOW,COMPLETION_SAMPLES,COMPLETION_GROUPS,COMPLETION_MODES,COMPLETION_ROUNDS))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       !headroom(qwen_direct_vm_pages(WINDOW,ALIGNMENT))||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("DIRECT_ALLOC_BEFORE bytes=%u",WINDOW))goto done;
    rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,ALIGNMENT,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();
    if(rc<0){if(physical>=0)retain();goto done;}if(physical<0)retain();
    if(!report("DIRECT_MAP_BEFORE bytes=%u",WINDOW))retain();
    rc=sceKernelMapDirectMemory((void **)&window,WINDOW,3,0,physical,ALIGNMENT);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc)||rc<0||!window||(uintptr_t)window%ALIGNMENT)retain();mapped=1;
    if(seteuid(1)||geteuid()!=1)goto finish;
    fd=open(COMPLETION_PACK,O_RDONLY|O_DIRECT|O_NOFOLLOW);
    if(fd<0||fstat(fd,&initial)||!S_ISREG(initial.st_mode)||!initial.st_ino||initial.st_size!=(off_t)COMPLETION_PACK_BYTES||
       (fcntl(fd,F_GETFL)&O_DIRECT)!=O_DIRECT)goto finish;
    initial_valid=1;
    sha256_t hash;sha256_init(&hash);
    for(uint64_t offset=0;offset<COMPLETION_PACK_BYTES;) {
        size_t bytes=COMPLETION_PACK_BYTES-offset;if(bytes>1u<<20)bytes=1u<<20;
        if(!headroom(0)||bytes%ALIGNMENT||!report("VERIFY_BEFORE bytes=%zu",bytes))goto finish;
        pending=1;ssize_t got=pread(fd,window,bytes,offset);pending=0;
        if(!report("VERIFY_RETURNED bytes=%lld",(long long)got))retain();
        if(got!=(ssize_t)bytes)goto finish;sha256_update(&hash,window,bytes);offset+=bytes;
    }
    unsigned char result[32];sha256_final(&hash,result);if(memcmp(result,completion_pack_SHA256,32))goto finish;
    if(!headroom(0)||!report("EOF_BEFORE"))goto finish;pending=1;
    ssize_t tail=pread(fd,window,ALIGNMENT,COMPLETION_PACK_BYTES);pending=0;
    if(!report("EOF_RETURNED bytes=%lld",(long long)tail))retain();if(tail!=0)goto finish;
    if(fstat(fd,&current)||!unchanged(&initial,&current)||!report("PACK_complete_SHA256_identity_EOF=1"))goto finish;
    unsigned char *destination=window+IO_BYTES;
    for(unsigned i=0;i<65536;++i){destination[2*i]=(unsigned char)i;destination[2*i+1]=(unsigned char)(i>>8);}
    for(unsigned i=0;i<65536;++i)if(destination[2*i]!=(unsigned char)i||destination[2*i+1]!=(unsigned char)(i>>8))goto finish;
    if(!report("ALL_65536_BF16_patterns_exact=1")||!headroom(0)||!completion_probe_start())retain();pool_started=1;
    const uint64_t started=completion_probe_now();if(!started)goto finish;
    for(unsigned round=0;round<COMPLETION_ROUNDS;++round)for(unsigned group=0;group<COMPLETION_GROUPS;++group)for(unsigned order=0;order<COMPLETION_MODES;++order) {
        const unsigned mode=(round+order)%COMPLETION_MODES;
        if(completion_probe_now()-started>UINT64_C(40000000000)||!headroom(0))goto finish;
        if(!report("BATCH_BEGIN round=%u group=%u mode=%u",round,group,mode))retain();
        struct completion_times t;
        const int completed=completion_probe_batch(fd,mode,completion_samples[group][mode>=2&&mode<4],COMPLETION_SAMPLES,window,destination,&t);
        if(completed<0)retain();if(!completed)goto finish;
        if(!report("BATCH_DRAINED round=%u group=%u mode=%u wall_ns=%llu restore_ns=%llu read_ns=%llu physical_bytes=%llu copy_ns=%llu",
           round,group,mode,(unsigned long long)t.wall_ns,(unsigned long long)t.restore_ns,
           (unsigned long long)t.read_ns,(unsigned long long)t.physical_bytes,(unsigned long long)t.copy_ns))retain();
        for(unsigned i=0;i<COMPLETION_SAMPLES;++i)if(!digest(destination+i*DESTINATION_STRIDE,QWEN_BF16_MATRIX_MAX,completion_raw_SHA256[group*COMPLETION_SAMPLES+i]))goto finish;
        if(fstat(fd,&current)||!unchanged(&initial,&current)||!report("BATCH_EXACT round=%u group=%u mode=%u complete_original_SHA256=%u",round,group,mode,COMPLETION_SAMPLES))goto finish;
    }
    ok=1;
finish:
    if(pending)retain();
    if(pool_started){if(!completion_probe_stop())retain();pool_stopped=1;}
    if(fd>=0){if(initial_valid&&(fstat(fd,&current)||!unchanged(&initial,&current)))ok=0;if(close(fd))retain();fd=-1;}
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom(0)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(pool_started&&!pool_stopped)retain();
    if(mapped) {
        if(!report("DIRECT_UNMAP_BEFORE"))retain();rc=sceKernelMunmap(window,WINDOW);
        if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        if(!report("DIRECT_RELEASE_BEFORE"))retain();rc=sceKernelReleaseDirectMemory(physical,WINDOW);
        if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;
    }
    if(!report("END success=%d nonce=%s pending_reads=0 all_workers_joined=%d Direct_released=%d GPU_calls=0 title_launches=0 automatic_retry=0",ok,CLOSE_NONCE,pool_stopped,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
