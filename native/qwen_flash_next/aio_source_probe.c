/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded read-only AIO comparison. No native title, model or GPU execution.
 */
#include "qualified_context_guard.c"
#include "aio_source_context.h"
#include "aio_read_lifecycle.h"
#include "source_contention_probe_io.h"
#include "hash/sha256/sha256.h"
#include <ps5platform/kernel.h>
#include <sys/stat.h>
#include <sys/resource.h>
#include <fcntl.h>
#include <time.h>

#define PAGE 16384u
#define STRIDE 3293184u
#define WINDOW (2u*STRIDE+2u*PAGE)
static int aio_pending,worker_pending;
static uint64_t clock_ns(int kind) {
    struct timespec t;if(clock_gettime(kind,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static void retain(void) {
    (void)report("RETAIN unknown_completion=1 aio_pending=%d worker_pending=%d no_cancel=1 no_retry=1",aio_pending,worker_pending);
    (void)fsync(output_fd);for(;;)usleep(1000000);
}
static int headroom(unsigned extra) {
    uint32_t a=0,b=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&a,&minimum,&reserved,&page,&b};
    for(unsigned i=0;i<5;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    const uint64_t required=(uint64_t)minimum+(reserved>256?reserved:256)+extra;
    int rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    if(!report("HEADROOM free_first=%u free_last=%u required=%llu flexible_bytes=%zu",a,b,(unsigned long long)required,flexible))return 0;
    return page==PAGE&&minimum&&reserved&&reserved<=minimum&&required<=UINT32_MAX&&a>=required&&b>=required&&!rc&&flexible>=(264u<<20);
}
static int identity(int fd,unsigned index) {
    struct stat s;if(fstat(fd,&s)||!S_ISREG(s.st_mode))return 0;
    const uint64_t actual[]={s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,(uint64_t)s.st_size,
        (uint64_t)s.st_mtim.tv_sec,(uint64_t)s.st_mtim.tv_nsec,(uint64_t)s.st_ctim.tv_sec,(uint64_t)s.st_ctim.tv_nsec};
    return !memcmp(actual,aio_sources[index].identity,sizeof(actual));
}
static int hash_matches(const void *at,size_t bytes,const char *expected) {
    sha256_t state;unsigned char raw[32];char text[65];sha256_init(&state);sha256_update(&state,at,bytes);sha256_final(&state,raw);
    for(unsigned i=0;i<32;++i){text[2*i]="0123456789abcdef"[raw[i]>>4];text[2*i+1]="0123456789abcdef"[raw[i]&15];}text[64]=0;
    return !strcmp(text,expected);
}
void probe_execute_read(struct job *j,unsigned role,int noop) {
    (void)role;memset(&j->sample,0,sizeof(j->sample));
    j->sample.begin=clock_ns(CLOCK_MONOTONIC);uint64_t cpu=clock_ns(CLOCK_THREAD_CPUTIME_ID);errno=0;
    j->sample.got=noop?(ssize_t)j->bytes:pread(j->fd,j->target,j->bytes,j->offset);j->sample.error=errno;
    j->sample.cpu_ns=clock_ns(CLOCK_THREAD_CPUTIME_ID)-cpu;j->sample.end=clock_ns(CLOCK_MONOTONIC);
}
/* The same lifecycle is fault-injected by the host check before native use. */
static int aio_read_once(struct qwen_aio_read *requests,unsigned count,int expect_invalid) {
    const struct qwen_aio_ops ops={sceKernelAioSubmitReadCommands,sceKernelAioWaitRequest,sceKernelAioDeleteRequest};
    int rc=qwen_aio_complete(&ops,requests,count,expect_invalid,&aio_pending);
    if(rc<0)retain();
    return rc;
}

int main(int argc,char **argv) {
    (void)argv;int ok=0,mapped=0,started=0,fd[2]={-1,-1};int64_t physical=-1;unsigned char *window=NULL;
    output_fd=open(AIO_SOURCE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s plan_sha256=%s Direct_bytes=%u pair_rounds=8 GPU_calls=0 title_launches=0",CLOSE_NONCE,AIO_SOURCE_PLAN_SHA,WINDOW))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       !headroom(1024)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    struct {uint64_t a;struct qwen_aio_param value;uint32_t pad;uint64_t b;} parameters={0};
    parameters.a=parameters.b=GUARD;sceKernelAioInitializeParam(&parameters.value);
    if(parameters.a!=GUARD||parameters.b!=GUARD)retain();
    for(unsigned i=0;i<3;++i) {
        struct qwen_aio_schedule *p=&parameters.value.priorities[i];
        if(p->window<1||p->window>128||p->delayed<0||p->delayed>128||p->split>1||p->size>0x1000000||p->chunk>0x1000000)goto done;
    }
    if(!report("AIO_INITIALIZE_BEFORE bytes=60 defaults_unchanged=1"))goto done;
    int rc=sceKernelAioInitializeImpl(&parameters.value,sizeof(parameters.value));
    if(!report("AIO_INITIALIZE_RETURNED rc=%d canaries=%d",rc,parameters.a==GUARD&&parameters.b==GUARD)||parameters.a!=GUARD||parameters.b!=GUARD)retain();
    if(rc)goto done;
    if(!headroom(512)||!report("DIRECT_ALLOC_BEFORE"))goto done;
    rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,PAGE,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();if(rc<0){if(physical>=0)retain();goto done;}if(rc||physical<0)retain();
    rc=sceKernelMapDirectMemory((void **)&window,WINDOW,3,0,physical,PAGE);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc)||rc||!window||(uintptr_t)window%PAGE)retain();mapped=1;memset(window,0xa7,WINDOW);
    struct {uint64_t a;struct qwen_aio_result value;uint64_t b;} results[2];
    memset(results,0,sizeof(results));for(unsigned i=0;i<2;++i)results[i].a=results[i].b=GUARD;
    struct qwen_aio_read requests[2]={{0,PAGE,window+PAGE,&results[0].value,-1,0},{0,0,NULL,NULL,-1,0}};
    if(!report("AIO_INVALID_FD_BEFORE requests=1 real_payload_reads=0"))goto finish;
    if(!aio_read_once(requests,1,1))goto finish;
    if(!report("AIO_INVALID_FD_COMPLETED value=%lld terminal=%u retired_once=1",(long long)results[0].value.value,results[0].value.state))retain();
    if(seteuid(1)||geteuid()!=1)goto finish;
    for(unsigned i=0;i<2;++i){fd[i]=open(aio_sources[i].path,O_RDONLY|O_DIRECT|O_NOFOLLOW);if(fd[i]<0||!identity(fd[i],i))goto finish;}
    if(!probe_cpp_start())retain();started=1;
    struct job jobs[2];memset(jobs,0,sizeof(jobs));
    for(unsigned i=0;i<2;++i){jobs[i].fd=fd[i];jobs[i].target=window+PAGE+i*STRIDE;jobs[i].bytes=STRIDE;jobs[i].offset=aio_sources[i].offset;}
    if(!probe_cpp_parallel_allowed(jobs,aio_sources[0].identity,aio_sources[1].identity))goto finish;
    const unsigned modes[]={0,1,1,0,0,1,1,0};
    for(unsigned round=0;round<8;++round) {
        if(!headroom(0)||!identity(fd[0],0)||!identity(fd[1],1)||!report("PAIR_BEFORE round=%u mode=%u",round,modes[round]))goto finish;
        memset(window+PAGE,0xa7,2u*STRIDE);memset(results,0,sizeof(results));for(unsigned i=0;i<2;++i)results[i].a=results[i].b=GUARD;
        for(unsigned i=0;i<2;++i)requests[i]=(struct qwen_aio_read){jobs[i].offset,STRIDE,jobs[i].target,&results[i].value,fd[i],0};
        const uint64_t begin=clock_ns(CLOCK_MONOTONIC);if(!begin)retain();int returned=0;
        if(modes[round])returned=aio_read_once(requests,2,0);
        else {worker_pending=1;returned=probe_cpp_read(jobs,0);if(!returned)retain();worker_pending=0;}
        const uint64_t end=clock_ns(CLOCK_MONOTONIC);if(!end||end<begin)retain();
        int hashes=returned;
        for(unsigned i=0;i<2;++i) {
            hashes&=results[i].a==GUARD&&results[i].b==GUARD&&identity(fd[i],i)&&
                hash_matches(jobs[i].target,STRIDE,aio_sources[i].envelope)&&
                hash_matches(jobs[i].target+aio_sources[i].residue,3276800,aio_sources[i].raw);
        }
        for(unsigned i=0;i<PAGE;++i)hashes&=window[i]==0xa7&&window[PAGE+2u*STRIDE+i]==0xa7;
        if(!report("PAIR_RETURNED round=%u mode=%u elapsed_ns=%llu bytes=%u original_hashes=%d identities=%d all_requests_retired=%d",round,modes[round],(unsigned long long)(end-begin),2u*STRIDE,hashes,identity(fd[0],0)&&identity(fd[1],1),!aio_pending&&!worker_pending))retain();
        if(!hashes)goto finish;
    }
    ok=1;
finish:
    if(aio_pending||worker_pending)retain();
    if(started){if(!probe_cpp_stop())retain();started=0;}
    for(unsigned i=0;i<2;++i)if(fd[i]>=0){if(!identity(fd[i],i))ok=0;if(close(fd[i]))retain();fd[i]=-1;}
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom(0)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(aio_pending||worker_pending||started)retain();
    if(mapped){int rc=sceKernelMunmap(window,WINDOW);if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        rc=sceKernelReleaseDirectMemory(physical,WINDOW);if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;}
    if(!report("END success=%d nonce=%s all_workers_joined=1 all_AIO_IDs_retired=1 Direct_released=%d GPU_calls=0 title_launches=0 no_retry=1",ok,CLOSE_NONCE,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
