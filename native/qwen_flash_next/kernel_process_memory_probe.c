/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded process RSS metadata. Shared RSS is not additive physical capacity.
 */
#include "qualified_context_guard.c"
#include "memory_probe_context.h"
#include "kernel_memory_trace.h"
#include <fcntl.h>
#include <time.h>
#define PROCESS_CAPACITY 512u
static struct {uint64_t before[2];unsigned char data[PROCESS_CAPACITY*sizeof(struct kinfo_proc)];uint64_t after[2];} inventory;
static unsigned queries,returned;
static int scalar(void *unused,const char *name,uint32_t *value) {
    (void)unused;size_t size=sizeof(*value);
    return !sysctlbyname(name,value,&size,NULL,0)&&size==sizeof(*value);
}
static int memory(unsigned phase) {
    struct timespec now;struct qwen_kernel_memory_sample s;
    if(clock_gettime(CLOCK_MONOTONIC,&now)||now.tv_sec<0||now.tv_nsec<0||now.tv_nsec>=1000000000||
       (uint64_t)now.tv_sec>UINT64_MAX/1000000000-1||
       !qwen_kernel_memory_observe(NULL,scalar,(uint64_t)now.tv_sec*UINT64_C(1000000000)+(uint64_t)now.tv_nsec,phase,&s))return 0;
    unsigned extra=(unsigned)((sizeof(inventory)+16383)/16384);
    return report("CATEGORIES phase=%u free_first=%u free_last=%u active=%u inactive=%u wired=%u cache=%u total=%u minimum=%u reserved=%u target=%u page_bytes=%u metadata_extra_pages=%u",
        phase,s.free_first,s.free_last,s.active,s.inactive,s.wired,s.cache,s.total,s.minimum,s.reserved,s.target,s.page_bytes,extra)&&qwen_kernel_memory_floor(&s,extra);
}
static int snapshot(unsigned phase) {
    inventory.before[0]=inventory.before[1]=inventory.after[0]=inventory.after[1]=GUARD;
    struct {uint64_t a;size_t value;uint64_t b;} length={GUARD,sizeof(inventory.data),GUARD};
    int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PROC,0};
    if(!report("INVENTORY_BEFORE phase=%u capacity=%zu",phase,sizeof(inventory.data))||fsync(output_fd))return 0;
    ++queries;errno=0;int rc=sysctl(mib,4,inventory.data,&length.value,NULL,0),error=errno;++returned;
    int intact=inventory.before[0]==GUARD&&inventory.before[1]==GUARD&&inventory.after[0]==GUARD&&inventory.after[1]==GUARD&&length.a==GUARD&&length.b==GUARD;
    if(!report("INVENTORY_RETURNED phase=%u rc=%d errno=%d bytes=%zu canaries=%d",phase,rc,error,length.value,intact)||fsync(output_fd)||
       rc||!intact||!length.value||length.value>sizeof(inventory.data)||length.value%sizeof(struct kinfo_proc))return 0;
    unsigned count=0,owners=0,self=0;
    for(size_t at=0;at<length.value;at+=sizeof(struct kinfo_proc)) {
        struct kinfo_proc k;memcpy(&k,inventory.data+at,sizeof(k));
        if(k.ki_structsize!=sizeof(k)||!memchr(k.ki_comm,0,sizeof(k.ki_comm))||k.ki_rssize<0||k.ki_numthreads<0)return 0;
        owners+=(unsigned)!strcmp(k.ki_comm,"eboot.bin");self+=(unsigned)(k.ki_pid==getpid());
        for(const unsigned char*p=(const unsigned char*)k.ki_comm;*p;++p)if(*p<32||*p>=127||*p=='=')return 0;
        if(!report("RSS phase=%u index=%u pid=%d ppid=%d start_sec=%lld start_usec=%lld name=%s state=%d virtual_bytes=%llu resident_pages=%lld threads=%d",
            phase,count,k.ki_pid,k.ki_ppid,(long long)k.ki_start.tv_sec,(long long)k.ki_start.tv_usec,k.ki_comm,(int)k.ki_stat,
            (unsigned long long)k.ki_size,(long long)k.ki_rssize,k.ki_numthreads))return 0;
        ++count;
    }
    return report("INVENTORY_COMPLETE phase=%u records=%u native_owners=%u self_records=%u",phase,count,owners,self)&&!owners&&self==1;
}
int main(int argc,char**argv) {
    (void)argv;int ok=0;
    output_fd=open(MEMORY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s metadata_only=1 allocations=0 payload_reads=0 title_launches=0 GPU_calls=0 maximum_queries=2",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1||!memory(0)||!snapshot(1))goto done;
    {const struct timespec delay={0,500000000};if(nanosleep(&delay,NULL))goto done;}
    if(!memory(1)||!snapshot(2)||!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1||!memory(2))goto done;
    ok=1;
done:
    if(!report("END success=%d nonce=%s inventory_queries=%u inventory_returned=%u allocations=0 payload_reads=0 title_launches=0 GPU_calls=0 automatic_retry=0",ok,CLOSE_NONCE,queries,returned))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
