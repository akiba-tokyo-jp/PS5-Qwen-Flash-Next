/* SPDX-License-Identifier: GPL-3.0-or-later
 * One CPU-only original-source qualification; no title/GPU/model execution.
 */
#include "qualified_context_guard.c"
#include "ready_CPU_context.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#define PAGE 16384u
#define STRIDE 3293184u
#define WINDOW (2u*STRIDE+2u*PAGE)
int ready_CPU_run(void *,size_t);
static int pending;
static void retain(void){(void)report("RETAIN unknown_source_or_Direct_completion=1 no_retry=1 GPU_calls=0");(void)fsync(output_fd);for(;;)usleep(1000000);}
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
int ready_CPU_permit(void){return headroom(0);}
int ready_CPU_record(const char *text) {
    const size_t n=strlen(text);if(n>65536||!healthy)return 0;
    if(write(output_fd,text,n)!=(ssize_t)n||write(output_fd,"\n",1)!=1||fsync(output_fd)){healthy=0;return 0;}return 1;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,mapped=0,rc=0;int64_t physical=-1;unsigned char *window=NULL;
    output_fd=open(READY_CPU_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s Direct_bytes=%u rounds=8 original_BF16=1 copies=0 GPU_calls=0 title_launches=0",CLOSE_NONCE,WINDOW))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
        !headroom(512+256)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("DIRECT_ALLOC_BEFORE")||fsync(output_fd))goto done;
    rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,PAGE,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();if(rc<0){if(physical>=0)retain();goto done;}if(physical<0)retain();
    if(!report("DIRECT_MAP_BEFORE")||fsync(output_fd))retain();
    rc=sceKernelMapDirectMemory((void **)&window,WINDOW,3,0,physical,PAGE);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc)||rc<0||!window||(uintptr_t)window%PAGE)retain();mapped=1;
    memset(window,0xa7,WINDOW);
    if(seteuid(1)||geteuid()!=1)goto finish;
    pending=1;rc=ready_CPU_run(window+PAGE,2u*STRIDE);if(rc<0)retain();pending=0;ok=rc==1;
    for(unsigned i=0;i<PAGE;++i)if(window[i]!=0xa7||window[PAGE+2u*STRIDE+i]!=0xa7)ok=0;
    if(!report("CPU_READS_RETURNED_AND_JOINED result=%d both_scratch_boundary_canaries=%d",rc,ok))retain();
finish:
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom(0)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(pending)retain();
    if(mapped) {
        if(!report("DIRECT_UNMAP_BEFORE")||fsync(output_fd))retain();rc=sceKernelMunmap(window,WINDOW);
        if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        if(!report("DIRECT_RELEASE_BEFORE")||fsync(output_fd))retain();rc=sceKernelReleaseDirectMemory(physical,WINDOW);
        if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;
    }
    if(!report("END success=%d nonce=%s all_workers_joined=1 Direct_released=%d pending_reads=0 GPU_calls=0 title_launches=0 no_retry=1",ok,CLOSE_NONCE,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
