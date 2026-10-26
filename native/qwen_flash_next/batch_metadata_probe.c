/* SPDX-License-Identifier: GPL-3.0-or-later
 * CPU-only metadata equivalence and timing under the qualified owner guard.
 */
#include "qualified_context_guard.c"
#include "batch_metadata_context.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#include <time.h>

extern int batch_metadata_test(void);
static uint64_t started;
static uint64_t now_ns(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
int batch_probe_permit(void) {
    uint32_t free_first=0,free_last=0,minimum=0,reserved=0,page=0;
    size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min",
        "vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&free_first,&minimum,&reserved,&page,&free_last};
    for(unsigned i=0;i<5;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    const uint64_t required=(uint64_t)minimum+(reserved>256?reserved:256)+64;
    const uint64_t current=now_ns();
    const int flexible_rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    if(!report("BATCH_HEADROOM free_first=%u free_last=%u minimum=%u reserved=%u required=%llu flexible_bytes=%zu rc=%d",
        free_first,free_last,minimum,reserved,(unsigned long long)required,flexible,flexible_rc))return 0;
    return page==16384&&minimum&&reserved&&reserved<=minimum&&required<=UINT32_MAX&&
        free_first>=required&&free_last>=required&&!flexible_rc&&
        flexible>=(264u<<20)&&current>=started&&current-started<=UINT64_C(20000000000);
}
int batch_probe_printf(const char *format,...) {
    char text[1024];
    va_list args;va_start(args,format);
    const int length=vsnprintf(text,sizeof(text),format,args);va_end(args);
    if(length<0||(size_t)length>=sizeof(text))return -1;
    if(!report("METADATA_FRAGMENT %s",text))return -1;
    return length;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,result=-1;
    output_fd=open(BATCH_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s maximum_CPP_live_bytes=1048576 Direct_allocations=0 payload_reads=0 title_launches=0 GPU_calls=0",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    started=now_ns();if(!started||!batch_probe_permit())goto done;
    if(!report("METADATA_BEFORE"))goto done;
    result=batch_metadata_test();
    if(!report("METADATA_RETURNED result=%d",result)||result||!batch_probe_permit())goto done;
    if(!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    ok=1;
done:
    if(!report("END success=%d result=%d nonce=%s CPU_metadata_only=1 title_launches=0 GPU_calls=0 no_retry=1",ok,result,CLOSE_NONCE))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;
    return ok?0:1;
}
