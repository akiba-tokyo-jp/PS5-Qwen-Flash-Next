/* SPDX-License-Identifier: GPL-3.0-or-later
 * Read-only memory-category snapshots; never infer that inactive pages are usable.
 */
#include "qualified_context_guard.c"
#include "memory_probe_context.h"
#include "kernel_memory_trace.h"
#include <fcntl.h>
#include <time.h>
static int scalar(void *unused,const char *name,uint32_t *value) {
    (void)unused;size_t bytes=sizeof(*value);
    return !sysctlbyname(name,value,&bytes,NULL,0)&&bytes==sizeof(*value);
}
int main(int argc,char **argv) {
    (void)argv;int ok=0;
    output_fd=open(MEMORY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s allocations=0 payload_reads=0 title_launches=0 GPU_calls=0",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    for(unsigned i=0;i<5;++i) {
        struct timespec now;struct qwen_kernel_memory_sample s;
        if(clock_gettime(CLOCK_MONOTONIC,&now)||now.tv_sec<0||now.tv_nsec<0||now.tv_nsec>=1000000000||
           (uint64_t)now.tv_sec>UINT64_MAX/1000000000-1||
           !qwen_kernel_memory_observe(NULL,scalar,(uint64_t)now.tv_sec*UINT64_C(1000000000)+(uint64_t)now.tv_nsec,0,&s))goto done;
        if(!report("CATEGORIES index=%u free_first=%u free_last=%u active=%u inactive=%u wired=%u cache=%u total=%u minimum=%u reserved=%u target=%u page_bytes=%u operational_floor_observed=%d",
            i,s.free_first,s.free_last,s.active,s.inactive,s.wired,s.cache,s.total,s.minimum,s.reserved,s.target,s.page_bytes,qwen_kernel_memory_floor(&s,0)))goto done;
        if(i<4){const struct timespec delay={0,250000000};if(nanosleep(&delay,NULL))goto done;}
    }
    if(!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    ok=1;
done:
    if(!report("END success=%d nonce=%s allocations=0 payload_reads=0 title_launches=0 GPU_calls=0 automatic_retry=0",ok,CLOSE_NONCE))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
