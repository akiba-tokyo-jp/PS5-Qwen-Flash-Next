/* SPDX-License-Identifier: MIT
 * CPU-only, fixed-extent diagnostic. No model loading or GPU operation.
 * The build supplies the pinned context guards, sealed file identities and
 * fresh one-shot paths. Never cancel or free an uncertain read's backing.
 */
#include "qualified_context_guard.c"
#include <sys/stat.h>
#include <sys/resource.h>
#include <pthread.h>
#include <stdatomic.h>
#include <fcntl.h>
#include <time.h>
#include <ps5platform/kernel.h>
#include "source_contention_context.h"
#include "source_contention_probe_io.h"
#ifndef PROBE_BOUNDARY
#define PROBE_BOUNDARY 0
#endif
#ifndef PROBE_SCHEDULE
#define PROBE_SCHEDULE 0
#endif
#ifndef PROBE_SPLIT
#define PROBE_SPLIT 0
#endif
#if PROBE_SPLIT
#include "hash/sha256/sha256.h"
#endif

#define HALF (4u << 20)
#define WINDOW (2u * HALF)
#define PAIRS 16u
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed=PTHREAD_COND_INITIALIZER;
static struct job pending_job;
static int pending,complete=1,stopping,ready;
static _Atomic int sampling,io_active,thread_ids[2];
static _Atomic unsigned current_mode;
struct wait_count { unsigned mode,role; char name[WMESGLEN+1]; unsigned count,object; int state; };
static struct wait_count waits[256];
/* Equality labels only; raw wait-object pointers are never logged or read. */
static uintptr_t indirect_objects[256];
static unsigned indirect_object_count;
static unsigned wait_entries,sample_calls,sample_errors,sample_unmatched;
static int sample_first_error;
extern int pthread_getthreadid_np(void);
static uint64_t now(int kind) {
    struct {uint64_t a;struct timespec t;uint64_t b;} g={GUARD,{0},GUARD};
    if(clock_gettime(kind,&g.t)||g.a!=GUARD||g.b!=GUARD||g.t.tv_sec<0||g.t.tv_nsec<0||g.t.tv_nsec>=1000000000)return 0;
    return (uint64_t)g.t.tv_sec*UINT64_C(1000000000)+(uint64_t)g.t.tv_nsec;
}
static int usage(struct rusage *out) {
    struct {uint64_t a[2];unsigned char bytes[512];uint64_t b[2];} g;
    memset(&g,0,sizeof(g));g.a[0]=g.a[1]=g.b[0]=g.b[1]=GUARD;
    _Static_assert(sizeof(*out)<=512,"Bounded thread usage ABI");
    if(getrusage(RUSAGE_THREAD,(struct rusage *)(void *)g.bytes)||g.a[0]!=GUARD||g.a[1]!=GUARD||g.b[0]!=GUARD||g.b[1]!=GUARD)return 0;
    memcpy(out,g.bytes,sizeof(*out));return 1;
}
static int headroom(void) {
    uint32_t free1=0,free2=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&free1,&minimum,&reserved,&page,&free2};
    for(unsigned i=0;i<5;++i){size_t bytes=4;if(sysctlbyname(names[i],values[i],&bytes,NULL,0)||bytes!=4){(void)report("HEADROOM query_failed=%u errno=%d bytes=%zu",i,errno,bytes);return 0;}}
    uint32_t extra=reserved>256?reserved:256;
    int rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    int ok=page==16384&&minimum&&minimum<=UINT32_MAX-extra&&free1>=minimum+extra&&free2>=minimum+extra&&!rc&&flexible>=(264u<<20);
    if(!ok)(void)report("HEADROOM admitted=0 page=%u free1=%u free2=%u minimum=%u reserved=%u extra=%u flexible_rc=%d flexible_bytes=%zu required_flexible_bytes=%u",page,free1,free2,minimum,reserved,extra,rc,flexible,264u<<20);
    return ok;
}
static void execute_read(struct job *j,int noop) {
    struct rusage a,b;memset(&j->sample,0,sizeof(j->sample));
    int have_a=usage(&a);uint64_t cpu=now(CLOCK_THREAD_CPUTIME_ID);
    j->sample.begin=now(CLOCK_MONOTONIC);errno=0;
    j->sample.got=noop?(ssize_t)j->bytes:pread(j->fd,j->target,j->bytes,j->offset);
    j->sample.error=errno;j->sample.end=now(CLOCK_MONOTONIC);
    uint64_t cpu_end=now(CLOCK_THREAD_CPUTIME_ID);
    j->sample.cpu_ns=cpu&&cpu_end>=cpu?cpu_end-cpu:0;
    if(have_a&&usage(&b)){j->sample.voluntary=b.ru_nvcsw-a.ru_nvcsw;j->sample.involuntary=b.ru_nivcsw-a.ru_nivcsw;}
}
void probe_execute_read(struct job *j,unsigned role,int noop) {
    thread_ids[role]=pthread_getthreadid_np();execute_read(j,noop);
}
static void *worker(void *unused) {
    (void)unused;thread_ids[1]=pthread_getthreadid_np();pthread_mutex_lock(&lock);ready=1;pthread_cond_broadcast(&changed);
    for(;;){while(!pending&&!stopping)pthread_cond_wait(&changed,&lock);if(stopping){pthread_mutex_unlock(&lock);return NULL;}
        struct job j=pending_job;int noop=j.fd<0;pthread_mutex_unlock(&lock);
        execute_read(&j,noop);
        pthread_mutex_lock(&lock);pending_job=j;pending=0;complete=1;pthread_cond_broadcast(&changed);}
}
static void *sampler(void *unused) {
    (void)unused;
    while(sampling){
        if(io_active){
            struct {uint64_t a[2];struct kinfo_proc rows[32];uint64_t b[2];} g;
            memset(&g,0,sizeof(g));g.a[0]=g.a[1]=g.b[0]=g.b[1]=GUARD;size_t bytes=sizeof(g.rows);
            /* PS5 rejected INC_THREAD in the preceding diagnostic. Query the
             * already qualified PID record and identify its actual thread. */
            int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PID,getpid()};
            ++sample_calls;
            int rc=sysctl(mib,4,g.rows,&bytes,NULL,0),saved_errno=errno;
            if(rc||bytes>sizeof(g.rows)||bytes%sizeof(g.rows[0])||
               g.a[0]!=GUARD||g.a[1]!=GUARD||g.b[0]!=GUARD||g.b[1]!=GUARD){++sample_errors;if(!sample_first_error)sample_first_error=rc?saved_errno:-1;}
            else for(size_t i=0;i<bytes/sizeof(g.rows[0]);++i){
                struct kinfo_proc *k=&g.rows[i];if(k->ki_structsize!=sizeof(*k)||k->ki_pid!=getpid()||!memchr(k->ki_wmesg,0,sizeof(k->ki_wmesg)))continue;
                if(k->ki_tid!=thread_ids[0]&&k->ki_tid!=thread_ids[1])++sample_unmatched;
                for(unsigned role=0;role<2;++role)if(k->ki_tid==thread_ids[role]){
                    unsigned object=0;
                    if(!strcmp(k->ki_wmesg,"BfsIpInd")&&k->ki_wchan){
                        uintptr_t value=(uintptr_t)k->ki_wchan;unsigned i=0;
                        for(;i<indirect_object_count;++i)if(indirect_objects[i]==value)break;
                        if(i==indirect_object_count&&i<256)indirect_objects[indirect_object_count++]=value;
                        if(i<256)object=i+1;else ++sample_errors;
                    }
                    unsigned index;for(index=0;index<wait_entries;++index)if(waits[index].mode==current_mode&&waits[index].role==role&&waits[index].object==object&&waits[index].state==k->ki_stat&&!strcmp(waits[index].name,k->ki_wmesg))break;
                    if(index==wait_entries&&index<256){waits[index].mode=current_mode;waits[index].role=role;waits[index].object=object;waits[index].state=k->ki_stat;strcpy(waits[index].name,k->ki_wmesg);++wait_entries;}
                    if(index<256)++waits[index].count;else ++sample_errors;
                }
            }
        }
        if(usleep(1000)){++sample_errors;return NULL;}
    }
    return NULL;
}
static int same(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_size==b->st_size&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int identity(int fd,unsigned index,struct stat *out) {
    if(fstat(fd,out)||!S_ISREG(out->st_mode)||out->st_size<=0||
       (!PROBE_SPLIT&&out->st_size<=(off_t)(1024u<<20)))return 0;
    const uint64_t actual[]={out->st_dev,out->st_ino,out->st_mode,out->st_uid,out->st_gid,(uint64_t)out->st_size,
        (uint64_t)out->st_mtim.tv_sec,(uint64_t)out->st_mtim.tv_nsec,(uint64_t)out->st_ctim.tv_sec,(uint64_t)out->st_ctim.tv_nsec};
    // Fresh experimental fragments have a whole-file host/transport SHA256 and
    // per-read original-byte hashes. Capture their current identity and require
    // the same descriptor identity at close; sealed model admission is unchanged.
    if(PROBE_SPLIT&&index>0)return actual[5]==probe_files[index].id[5];
    return !memcmp(actual,probe_files[index].id,sizeof(actual));
}
static void retain_uncertain(void) {
    (void)report("UNCERTAIN worker_backing_retained=1 read_retry=0 GPU_calls=0");
    for(;;)sleep(1);
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,work_ok=1,mapped=0,worker_started=0,worker_joined=0;pthread_t io_thread,monitor;int fd[3]={-1,-1,-1};struct stat original[3];
    void *window=NULL;int64_t physical=-1;uint64_t started=0;
    output_fd=open(PROBE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s uid=%u euid=%u constructors=%u CPU_only=1 window_bytes=%u model_loaded=0 GPU_calls=0 title_launches=0",CLOSE_NONCE,getuid(),geteuid(),constructors,WINDOW))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||!headroom())goto done;
    int big=sceSystemServiceGetAppIdOfRunningBigApp();if(!report("IDLE BigApp=%d",big)||big!=-1)goto done;
    int allocation_rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT allocation_returned=1 rc=%d bytes=%u",allocation_rc,WINDOW)||allocation_rc||physical<0)goto done;
    int mapping_rc=sceKernelMapDirectMemory(&window,WINDOW,3,0,physical,16384);
    if(!report("DIRECT mapping_returned=1 rc=%d aligned=%d",mapping_rc,window&&!((uintptr_t)window%16384))||mapping_rc||!window||((uintptr_t)window%16384))goto done;
    mapped=1;
    if(seteuid(1)||geteuid()!=1)goto done;
    for(unsigned i=0;i<3;++i){unsigned file=PROBE_SPLIT?i:(i==2?1:0);fd[i]=open(probe_files[file].path,O_RDONLY|O_DIRECT|O_NOFOLLOW);int opened=fd[i]>=0,valid=opened&&identity(fd[i],file,&original[i]);if(!report("SOURCE index=%u opened=%d identity=%d errno=%d",i,opened,valid,errno)||!valid)goto done;}
    if(PROBE_SPLIT) {
        if(original[0].st_dev!=original[1].st_dev||original[0].st_dev!=original[2].st_dev||
           original[0].st_ino==original[1].st_ino||original[0].st_ino==original[2].st_ino||original[1].st_ino==original[2].st_ino)goto done;
    } else if(original[0].st_ino!=original[1].st_ino||original[0].st_ino==original[2].st_ino)goto done;
    thread_ids[0]=pthread_getthreadid_np();
    if(PROBE_CPP){if(!probe_cpp_start())retain_uncertain();worker_started=1;}
    else{if(pthread_create(&io_thread,NULL,worker,NULL))goto done;worker_started=1;
        pthread_mutex_lock(&lock);while(!ready)pthread_cond_wait(&changed,&lock);pthread_mutex_unlock(&lock);}
    sampling=PROBE_SPLIT?0:1;if(pthread_create(&monitor,NULL,sampler,NULL))retain_uncertain();
    started=now(CLOCK_MONOTONIC);if(!started)retain_uncertain();
    for(unsigned round=0;round<3;++round)for(unsigned order=0;order<PROBE_MODES;++order){
        unsigned mode=round%2?PROBE_MODES-1-order:order;current_mode=mode;
        /* Default geometry controls; PROBE_BOUNDARY replaces these recipes.
         * 0: no-op handoff, 1/2: serial/parallel same descriptor,
         * 3/4: serial/parallel independent opens of the same vnode,
         * 5/6: serial/parallel different vnodes; 7/8 and 9/10: adjacent
         * experts with a shared alignment page, same/separate descriptors. */
        for(unsigned pair=0;pair<PAIRS;++pair){
            const uint64_t diagnostic_limit=PROBE_SPLIT?UINT64_C(45000000000):UINT64_C(30000000000);
            if(!headroom()||now(CLOCK_MONOTONIC)-started>diagnostic_limit){work_ok=0;goto finish;}
            int different=mode==5||mode==6;
            int second=different?fd[2]:(mode==3||mode==4||mode>=9)?fd[1]:fd[0];
            int first_fd=fd[0];
            unsigned expert=11+pair*29,distance=mode>=7?1:8;
            off_t first=(off_t)probe_geometry[0].base+(off_t)expert*probe_geometry[0].expert_bytes;
            off_t second_offset=(off_t)probe_geometry[different].base+(off_t)(expert+distance)*probe_geometry[different].expert_bytes;
            size_t bytes=probe_geometry[0].read_bytes;
            int parallel=!mode||!(mode&1);
#if PROBE_BOUNDARY
            const struct boundary_case * control=&boundary_cases[mode];
            first_fd=fd[control->main_descriptor];
            second=fd[control->descriptor];
            first=(off_t)control->offset0+(off_t)pair*16384;
            second_offset=(off_t)control->offset1+(off_t)pair*16384;
            parallel=control->parallel;
#if PROBE_SCHEDULE
            bytes=control->bytes;
            first=(off_t)control->offset0+(off_t)pair*control->stride;
            second_offset=(off_t)control->offset1+(off_t)pair*control->stride;
#endif
#endif
            struct job jobs[2]={{.fd=(mode||PROBE_CPP)?first_fd:-1,.target=window,.bytes=bytes,.offset=first},
                {.fd=(mode||PROBE_CPP)?second:-1,.target=(unsigned char *)window+HALF,.bytes=bytes,.offset=second_offset}};
#if PROBE_SCHEDULE
            if(control->parallel==3){parallel=0;jobs[1].bytes=0;}
            else if(control->parallel==2)parallel=probe_cpp_parallel_allowed(jobs,
                probe_files[control->main_descriptor==2?1:0].id,probe_files[control->descriptor==2?1:0].id);
#endif
            uint64_t begin=now(CLOCK_MONOTONIC),dispatch=0,wait=0,worker_end=0;
            /* The final round leaves the sampler asleep as a perturbation control. */
            io_active=round!=2;
            if(parallel&&PROBE_CPP){
                if(!probe_cpp_read(jobs,!mode))retain_uncertain();
                uint64_t returned=now(CLOCK_MONOTONIC);dispatch=jobs[1].sample.begin-begin;
                wait=returned-jobs[0].sample.end;worker_end=jobs[1].sample.end;
            }else if(parallel){
                pthread_mutex_lock(&lock);pending_job=jobs[1];pending=1;complete=0;pthread_cond_broadcast(&changed);pthread_mutex_unlock(&lock);
                execute_read(&jobs[0],!mode);uint64_t wait_at=now(CLOCK_MONOTONIC);
                pthread_mutex_lock(&lock);struct timespec deadline;if(clock_gettime(CLOCK_REALTIME,&deadline))retain_uncertain();deadline.tv_sec+=2;
                while(!complete){int rc=pthread_cond_timedwait(&changed,&lock,&deadline);if(rc&&!complete)retain_uncertain();}
                jobs[1]=pending_job;pthread_mutex_unlock(&lock);wait=now(CLOCK_MONOTONIC)-wait_at;
                dispatch=jobs[1].sample.begin-begin;worker_end=jobs[1].sample.end;
            }else{execute_read(&jobs[0],0);if(jobs[1].bytes)execute_read(&jobs[1],0);}
            uint64_t end=now(CLOCK_MONOTONIC);io_active=0;
            uint64_t overlap_start=jobs[0].sample.begin>jobs[1].sample.begin?jobs[0].sample.begin:jobs[1].sample.begin;
            uint64_t overlap_end=jobs[0].sample.end<jobs[1].sample.end?jobs[0].sample.end:jobs[1].sample.end;
            uint64_t overlap=overlap_end>overlap_start?overlap_end-overlap_start:0;
            if(jobs[0].sample.got!=(ssize_t)jobs[0].bytes||jobs[1].sample.got!=(ssize_t)jobs[1].bytes){work_ok=0;goto finish;}
#if PROBE_SPLIT
            // SHA256 covers every returned byte; hashing is outside the timed
            // read interval and no extra source payload window is allocated.
            for(unsigned i=0;i<2;++i) {
                sha256_t hash;unsigned char digest[32];sha256_init(&hash);
                sha256_update(&hash,jobs[i].target,jobs[i].bytes);sha256_final(&hash,digest);
                if(memcmp(digest,expected_read_hashes[pair][i],32)){work_ok=0;goto finish;}
            }
#endif
            if(!report("PAIR round=%u mode=%u pair=%u bytes=%u wall_ns=%llu p0_ns=%llu p1_ns=%llu cpu0_ns=%llu cpu1_ns=%llu overlap_ns=%llu dispatch_ns=%llu wait_ns=%llu after_worker_ns=%llu nv0=%ld nv1=%ld ni0=%ld ni1=%ld e0=%d e1=%d parallel=%d calls=%u",
                round,mode,pair,(unsigned)(jobs[0].bytes+jobs[1].bytes),(unsigned long long)(end-begin),(unsigned long long)(jobs[0].sample.end-jobs[0].sample.begin),
                (unsigned long long)(jobs[1].sample.end-jobs[1].sample.begin),(unsigned long long)jobs[0].sample.cpu_ns,(unsigned long long)jobs[1].sample.cpu_ns,
                (unsigned long long)overlap,(unsigned long long)dispatch,(unsigned long long)wait,(unsigned long long)(worker_end&&end>=worker_end?end-worker_end:0),
                jobs[0].sample.voluntary,jobs[1].sample.voluntary,jobs[0].sample.involuntary,jobs[1].sample.involuntary,jobs[0].sample.error,jobs[1].sample.error,parallel,jobs[1].bytes?2U:1U))retain_uncertain();
        }
    }
finish:
    io_active=0;sampling=0;if(pthread_join(monitor,NULL))retain_uncertain();
    if(PROBE_CPP){if(!probe_cpp_stop())retain_uncertain();worker_joined=1;}
    else{pthread_mutex_lock(&lock);if(pending||!complete)retain_uncertain();stopping=1;pthread_cond_broadcast(&changed);pthread_mutex_unlock(&lock);
        if(pthread_join(io_thread,NULL))retain_uncertain();worker_joined=1;}
    for(unsigned i=0;i<wait_entries;++i)if(!report("WAIT mode=%u role=%u name=%s samples=%u state=%d object=%u",waits[i].mode,waits[i].role,waits[i].name,waits[i].count,waits[i].state,waits[i].object))goto done;
    if(!report("SAMPLER calls=%u errors=%u first_errno=%d unmatched=%u interval_us=1000 worker_joined=1",sample_calls,sample_errors,sample_first_error,sample_unmatched))goto done;
    for(unsigned i=0;i<3;++i){struct stat after;if(fstat(fd[i],&after)||!same(&original[i],&after)||close(fd[i]))goto done;fd[i]=-1;}
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom()||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    ok=work_ok;
done:
    if(worker_started&&!worker_joined)retain_uncertain();
    for(unsigned i=0;i<3;++i)if(fd[i]>=0){int rc=close(fd[i]);fd[i]=-1;if(rc)ok=0;}
    /* Only a positively mapped, unused or fully joined window is releasable.
     * A failed map/unmap retains its allocation. No operation is retried. */
    if(mapped){int rc=sceKernelMunmap(window,WINDOW);mapped=0;
        if(rc)ok=0;
        else{rc=sceKernelReleaseDirectMemory(physical,WINDOW);if(rc)ok=0;else{physical=-1;window=NULL;}}
        if(!report("DIRECT known_completion_cleanup_returned=1 fully_released=%d",physical<0))ok=0;}
    if(!report("END success=%d nonce=%s worker_active=%d model_loaded=0 GPU_calls=0 title_launches=0 read_retries=0",ok,CLOSE_NONCE,pending))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;
    return ok?0:1;
}
