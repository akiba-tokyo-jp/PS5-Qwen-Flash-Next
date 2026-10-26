/* SPDX-License-Identifier: GPL-3.0-or-later
 * Paired original-BF16 delivery: qualified two-lane reads versus one preadv.
 */
#include "qualified_context_guard.c"
#include "vector_delivery_context.h"
#include "completion_probe_io.h"
#include "hash/sha256/sha256.h"
#include <ps5platform/kernel.h>
#include <sys/uio.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>
#define PAGE 16384u
#define STRIDE 3293184u
#define MATRIX 3276800u
#define SCRATCH (1u<<20)
#define WINDOW (12u<<20)
static int pending,worker_started,worker_stopped;
static uint64_t vector_id=UINT64_C(1)<<63;
uint64_t completion_probe_now(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static void retain(void) {
    (void)report("RETAIN source_and_Direct_backing=1 no_retry=1 GPU_calls=0");for(;;)usleep(1000000);
}
static int headroom(unsigned extra) {
    uint32_t a=0,b=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&a,&minimum,&reserved,&page,&b};
    for(unsigned i=0;i<5;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    const uint64_t required=(uint64_t)minimum+(reserved>256?reserved:256)+extra;
    const int rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    if(extra&&!report("PREALLOC_HEADROOM free_first=%u free_last=%u required=%llu flexible_bytes=%zu rc=%d",a,b,(unsigned long long)required,flexible,rc))return 0;
    return page==PAGE&&minimum&&reserved&&reserved<=minimum&&required<=UINT32_MAX&&a>=required&&b>=required&&!rc&&flexible>=(264u<<20);
}
int completion_probe_permit(void){return headroom(0);}
int completion_probe_event(unsigned returned,unsigned slot,uint64_t id,uint64_t offset,uint64_t bytes,int64_t result,uint64_t a,uint64_t b) {
    return report("IO_%s slot=%u id=%llu offset=%llu bytes=%llu result=%lld start_ns=%llu end_ns=%llu",
        returned?"RETURNED":"BEFORE",slot,(unsigned long long)id,(unsigned long long)offset,
        (unsigned long long)bytes,(long long)result,(unsigned long long)a,(unsigned long long)b);
}
static int identity(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&
        a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
        a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int digest(const void *data,size_t bytes,const unsigned char expected[32]) {
    sha256_t hash;unsigned char actual[32];sha256_init(&hash);sha256_update(&hash,data,bytes);sha256_final(&hash,actual);
    return !memcmp(actual,expected,32);
}
static int vector_batch(int fd,const struct completion_extent *extents,unsigned char *destination,struct completion_times *times) {
    struct iovec vectors[3];
    for(unsigned i=0;i<3;++i) {
        if(extents[i].bytes!=MATRIX||extents[i].requested!=STRIDE||extents[i].offset!=(uint64_t)extents[0].offset+i*STRIDE)return 0;
        vectors[i].iov_base=destination+i*STRIDE;vectors[i].iov_len=STRIDE;
    }
    if(!headroom(0))return 0;
    const uint64_t begin=completion_probe_now(),id=++vector_id;
    if(!begin||!completion_probe_event(0,0,id,extents[0].offset,3u*STRIDE,0,0,0))return 0;
    const uint64_t a=completion_probe_now();pending=1;
    const ssize_t got=preadv(fd,vectors,3,extents[0].offset);pending=0;
    const uint64_t b=completion_probe_now();
    if(!completion_probe_event(1,0,id,extents[0].offset,3u*STRIDE,got,a,b))return -1;
    if(!a||b<a||got!=3u*STRIDE)return 0;
    const uint64_t end=completion_probe_now();if(end<b)return -1;
    memset(times,0,sizeof(*times));times->wall_ns=end-begin;times->read_ns=b-a;times->physical_bytes=3u*STRIDE;
    return 1;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,mapped=0,fd=-1,initial_valid=0,rc=0;int64_t physical=-1;unsigned char *window=NULL;
    struct stat before={0},after={0};
    output_fd=open(VECTOR_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s Direct_bytes=%u samples=9 groups=3 modes=2 rounds=8 original_BF16=1 copies=0 GPU_calls=0 title_launches=0",CLOSE_NONCE,WINDOW))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
        !headroom(WINDOW/PAGE)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("DIRECT_ALLOC_BEFORE"))goto done;
    rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,PAGE,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();if(rc<0){if(physical>=0)retain();goto done;}if(physical<0)retain();
    if(!report("DIRECT_MAP_BEFORE"))retain();rc=sceKernelMapDirectMemory((void **)&window,WINDOW,3,0,physical,PAGE);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc)||rc<0||!window||(uintptr_t)window%PAGE)retain();mapped=1;
    if(seteuid(1)||geteuid()!=1)goto finish;
    fd=open(VECTOR_PACK,O_RDONLY|O_DIRECT|O_NOFOLLOW);
    if(fd<0||fstat(fd,&before)||!S_ISREG(before.st_mode)||!before.st_ino||before.st_size!=(off_t)VECTOR_PACK_BYTES||
        (fcntl(fd,F_GETFL)&O_DIRECT)!=O_DIRECT)goto finish;
    initial_valid=1;sha256_t hash;sha256_init(&hash);
    for(uint64_t offset=0;offset<VECTOR_PACK_BYTES;) {
        size_t n=VECTOR_PACK_BYTES-offset;if(n>SCRATCH)n=SCRATCH;
        if(!headroom(0)||n%PAGE||!report("VERIFY_BEFORE bytes=%zu",n))goto finish;
        pending=1;const ssize_t got=pread(fd,window,n,offset);pending=0;
        if(!report("VERIFY_RETURNED bytes=%lld",(long long)got))retain();if(got!=(ssize_t)n)goto finish;
        sha256_update(&hash,window,n);offset+=n;
    }
    unsigned char pack_hash[32];sha256_final(&hash,pack_hash);if(memcmp(pack_hash,vector_pack_SHA256,32))goto finish;
    if(!report("EOF_BEFORE"))goto finish;pending=1;const ssize_t tail=pread(fd,window,PAGE,VECTOR_PACK_BYTES);pending=0;
    if(!report("EOF_RETURNED bytes=%lld",(long long)tail))retain();if(tail)goto finish;
    if(fstat(fd,&after)||!identity(&before,&after)||!report("PACK_complete_SHA256_identity_EOF=1"))goto finish;
    if(!headroom(0)||!completion_probe_start())retain();worker_started=1;
    const uint64_t start=completion_probe_now();if(!start)goto finish;
    unsigned char *destination=window+SCRATCH;
    for(unsigned round=0;round<8;++round)for(unsigned shifted=0;shifted<3;++shifted)for(unsigned order=0;order<2;++order) {
        const unsigned group=(round+shifted)%3,mode=(round+order)%2;
        if(completion_probe_now()-start>UINT64_C(40000000000)||!headroom(0))goto finish;
        memset(destination,0xa7,WINDOW-SCRATCH);
        if(!report("BATCH_BEGIN round=%u group=%u mode=%u",round,group,mode))retain();
        struct completion_times times;int result;
        if(mode==0)result=completion_probe_batch(fd,0,vector_samples[group],3,window,destination,&times);
        else result=vector_batch(fd,vector_samples[group],destination,&times);
        if(result<0)retain();if(!result)goto finish;
        if(!report("BATCH_DRAINED round=%u group=%u mode=%u wall_ns=%llu read_ns=%llu physical_bytes=%llu copies=0",
            round,group,mode,(unsigned long long)times.wall_ns,(unsigned long long)times.read_ns,(unsigned long long)times.physical_bytes))retain();
        for(unsigned i=0;i<3;++i) {
            if(!digest(destination+i*STRIDE+vector_residue[group][i],MATRIX,vector_raw_SHA256[group][i])||
                !digest(destination+i*STRIDE,STRIDE,vector_envelope_SHA256[group][i]))goto finish;
        }
        for(unsigned i=3*STRIDE;i<WINDOW-SCRATCH;++i)if(destination[i]!=0xa7)goto finish;
        if(fstat(fd,&after)||!identity(&before,&after)||!report("BATCH_EXACT round=%u group=%u mode=%u original_SHA256=3 envelope_SHA256=3 tail_canary=1",round,group,mode))goto finish;
    }
    ok=1;
finish:
    if(pending)retain();if(worker_started){if(!completion_probe_stop())retain();worker_stopped=1;}
    if(fd>=0){if(initial_valid&&(fstat(fd,&after)||!identity(&before,&after)))ok=0;if(close(fd))retain();fd=-1;}
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom(0)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(worker_started&&!worker_stopped)retain();
    if(mapped){if(!report("DIRECT_UNMAP_BEFORE"))retain();rc=sceKernelMunmap(window,WINDOW);if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        if(!report("DIRECT_RELEASE_BEFORE"))retain();rc=sceKernelReleaseDirectMemory(physical,WINDOW);if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;}
    if(!report("END success=%d nonce=%s all_workers_joined=%d Direct_released=%d pending_reads=0 GPU_calls=0 title_launches=0 no_retry=1",ok,CLOSE_NONCE,worker_stopped,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
