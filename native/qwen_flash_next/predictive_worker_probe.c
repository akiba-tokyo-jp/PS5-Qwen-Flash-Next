/* SPDX-License-Identifier: GPL-3.0-or-later
 * Actual persistent worker and three sealed original BF16 roles. No GPU/model.
 */
#include "qualified_context_guard.c"
#include "predictive_worker_context.h"
#include "source_contention_probe_io.h"
#include <ps5platform/kernel.h>
#include "hash/sha256/sha256.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#define PAGE 16384u
#define STRIDE 3293184u
#define WINDOW (3u*STRIDE+2u*PAGE)
extern int predictive_worker_start(void);
extern int predictive_worker_submit(const struct job *);
extern int predictive_worker_complete(struct job *);
extern int predictive_worker_stop(void);
extern int predictive_worker_foreground_cost_control(void);
static int pending;
static uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;}
static void retain(void){(void)report("RETAIN unknown_completion=1 worker_pending=%d no_cancel=1 no_retry=1",pending);
    (void)fsync(output_fd);for(;;)usleep(1000000);}
static int headroom(unsigned extra,int log){uint32_t a=0,b=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&a,&minimum,&reserved,&page,&b};
    for(unsigned i=0;i<5;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    uint64_t required=(uint64_t)minimum+(reserved>256?reserved:256)+extra;
    int rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    if(log&&!report("HEADROOM free_first=%u free_last=%u required=%llu flexible_bytes=%zu",a,b,(unsigned long long)required,flexible))return 0;
    return page==PAGE&&minimum&&reserved&&reserved<=minimum&&required<=UINT32_MAX&&a>=required&&b>=required&&!rc&&flexible>=(264u<<20);}
static int identity(int fd,unsigned i){struct stat s;if(fstat(fd,&s)||!S_ISREG(s.st_mode))return 0;
    const uint64_t value[]={s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,(uint64_t)s.st_size,
        (uint64_t)s.st_mtim.tv_sec,(uint64_t)s.st_mtim.tv_nsec,(uint64_t)s.st_ctim.tv_sec,(uint64_t)s.st_ctim.tv_nsec};
    return !memcmp(value,predictive_sources[i].identity,sizeof(value));}
static int hash(const void *at,size_t bytes,const char *expected){sha256_t s;unsigned char raw[32];char text[65];
    sha256_init(&s);sha256_update(&s,at,bytes);sha256_final(&s,raw);
    for(unsigned i=0;i<32;++i){text[2*i]="0123456789abcdef"[raw[i]>>4];text[2*i+1]="0123456789abcdef"[raw[i]&15];}text[64]=0;return !strcmp(text,expected);}
void probe_execute_read(struct job *j,unsigned role,int noop){(void)noop;memset(&j->sample,0,sizeof(j->sample));
    j->sample.begin=now();errno=0;
    if(role>=3||!headroom(0,0)||!identity(j->fd,role)){j->sample.got=-1;j->sample.error=EINVAL;}
    else {j->sample.got=pread(j->fd,j->target,j->bytes,j->offset);j->sample.error=errno;}
    j->sample.end=now();}
int main(int argc,char **argv){(void)argv;int ok=0,mapped=0,started=0;unsigned completed_jobs=0;int fd[3]={-1,-1,-1};int64_t physical=-1;unsigned char *window=NULL;
    output_fd=open(PREDICTIVE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s plan_sha256=%s Direct_bytes=%u rounds=4 roles=3 GPU_calls=0 title_launches=0",CLOSE_NONCE,PREDICTIVE_PLAN_SHA,WINDOW))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||!headroom(1280,1)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("DIRECT_ALLOC_BEFORE bytes=%u",WINDOW))goto done;
    int rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,PAGE,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();if(rc<0){if(physical>=0)retain();goto done;}if(rc||physical<0)retain();
    rc=sceKernelMapDirectMemory((void **)&window,WINDOW,3,0,physical,PAGE);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc)||rc||!window||(uintptr_t)window%PAGE)retain();mapped=1;memset(window,0xa7,WINDOW);
    if(seteuid(1)||geteuid()!=1)goto finish;
    for(unsigned i=0;i<3;++i){fd[i]=open(predictive_sources[i].path,O_RDONLY|O_DIRECT|O_NOFOLLOW);if(fd[i]<0||!identity(fd[i],i))goto finish;}
    if(!headroom(512,1)||!report("WORKER_START_BEFORE"))goto finish;
    if(!predictive_worker_start()){if(!report("WORKER_START_REFUSED known_no_job=1"))retain();goto finish;}started=1;
    if(!report("WORKER_START_RETURNED persistent=1"))retain();
    for(unsigned round=0;round<4;++round){struct job jobs[3];memset(jobs,0,sizeof(jobs));
        if(!headroom(0,1))goto finish;
        for(unsigned i=0;i<3;++i){jobs[i].fd=fd[i];jobs[i].target=window+PAGE+i*STRIDE;jobs[i].bytes=STRIDE;jobs[i].offset=predictive_sources[i].offset;}
        memset(window+PAGE,0xa7,3u*STRIDE);
        if(!report("JOB_BEFORE round=%u roles=3 expected_bytes=%u",round,3u*STRIDE))goto finish;
        pending=1;const uint64_t begin=now();
        if(!begin||!predictive_worker_submit(jobs))retain();
        int foreground=predictive_worker_foreground_cost_control();
        const uint64_t join=now();if(!predictive_worker_complete(jobs))retain();pending=0;
        const uint64_t end=now();if(!join||!end||join<begin||end<join)retain();++completed_jobs;
        int exact=foreground;
        for(unsigned role=0;role<3;++role){struct read_sample *s=&jobs[role].sample;
            exact&=s->got==STRIDE&&!s->error&&s->begin>=begin&&s->end>=s->begin&&s->end<=end&&identity(fd[role],role)&&
                hash(jobs[role].target,STRIDE,predictive_sources[role].envelope)&&
                hash(jobs[role].target+predictive_sources[role].residue,3276800,predictive_sources[role].raw);
            if(!report("ROLE_RETURNED round=%u role=%u bytes=%lld errno=%d begin_ns=%llu end_ns=%llu",round,role,(long long)s->got,s->error,
                (unsigned long long)s->begin,(unsigned long long)s->end))retain();}
        for(unsigned i=0;i<PAGE;++i)exact&=window[i]==0xa7&&window[PAGE+3u*STRIDE+i]==0xa7;
        if(!report("JOB_RETURNED round=%u elapsed_ns=%llu foreground_ns=%llu wait_ns=%llu exact_hashes_and_canaries=%d foreground_cost_control=%d pending=0",round,
            (unsigned long long)(end-begin),(unsigned long long)(join-begin),(unsigned long long)(end-join),exact,foreground))retain();
        if(!exact)goto finish;
    }
    ok=1;
finish:
    if(pending)retain();if(started){if(!predictive_worker_stop())retain();started=0;if(!report("WORKER_JOINED persistent_lifetimes=1 jobs=%u",completed_jobs))retain();}
    for(unsigned i=0;i<3;++i)if(fd[i]>=0){if(!identity(fd[i],i))ok=0;if(close(fd[i]))retain();fd[i]=-1;}
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom(0,1)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(pending||started)retain();
    if(mapped){int rc=sceKernelMunmap(window,WINDOW);if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        rc=sceKernelReleaseDirectMemory(physical,WINDOW);if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;}
    if(!report("END success=%d nonce=%s worker_joined=1 Direct_released=%d GPU_calls=0 title_launches=0 no_retry=1",ok,CLOSE_NONCE,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;}
