/* SPDX-License-Identifier: MIT
 * Compare new ordinary/Direct evidence files; never touch a model or title.
 */
#include "qualified_context_guard.c"
#include "frame_output_context.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#include <time.h>
#define FRAME_WINDOW (1u<<20)
extern int frame_probe_write(const char *,void *,int);
extern int frame_probe_verify(const char *,void *);
int frame_probe_stage(const char *text){return report("FRAME_STAGE %s",text);}
static int sample(uint32_t *free_pages){
    uint32_t minimum=0,reserved=0,page=0;size_t flexible=0;
    uint32_t *values[]={free_pages,&minimum,&reserved,&page};
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize"};
    for(unsigned i=0;i<4;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    const uint32_t extra=reserved>256?reserved:256;
    return page==16384&&minimum&&reserved&&reserved<=minimum&&minimum<=UINT32_MAX-extra&&
        *free_pages>=minimum+extra&&!sceKernelAvailableFlexibleMemorySize(&flexible)&&flexible>=(264u<<20);
}
int frame_probe_guard(void){uint32_t free_pages=0;return sample(&free_pages);}
static void retain(void){(void)report("RETAIN frame_evidence_backing=1 no_retry=1 GPU_calls=0");for(;;)usleep(1000000);}
int main(int argc,char **argv){
    (void)argv;int ok=0,mapped=0;int64_t physical=-1;void *window=NULL;
    output_fd=open(FRAME_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s frame_evidence_only=1 window_bytes=%u GPU_calls=0 title_launches=0",CLOSE_NONCE,FRAME_WINDOW))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       !frame_probe_guard()||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("FRAME_ALLOC_BEFORE"))goto done;
    int rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),FRAME_WINDOW,16384,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("FRAME_ALLOC_RETURNED rc=%d",rc))retain();if(rc<0){if(physical>=0)retain();goto done;}if(physical<0)retain();
    if(!report("FRAME_MAP_BEFORE"))retain();rc=sceKernelMapDirectMemory(&window,FRAME_WINDOW,3,0,physical,16384);
    if(!report("FRAME_MAP_RETURNED rc=%d",rc)||rc<0||!window||(uintptr_t)window%16384)retain();mapped=1;
    for(unsigned round=0;round<2;++round)for(unsigned order=0;order<2;++order){
        unsigned mode=(round+order)%2,index=round*2+order;uint32_t before=0,after_write=0,after_verify=0;
        if(!sample(&before)||!report("FRAME_CASE_BEFORE round=%u mode=%u index=%u free=%u",round,mode,index,before))goto done;
        if(!frame_probe_write(frame_paths[index],window,(int)mode))retain();
        if(!sample(&after_write)||!report("FRAME_CASE_WRITTEN round=%u mode=%u index=%u free=%u",round,mode,index,after_write))retain();
        if(!frame_probe_verify(frame_paths[index],window)||!sample(&after_verify))retain();
        if(!report("FRAME_CASE_COMPLETE round=%u mode=%u index=%u bytes=8294454 writes=8 SHA256_exact=1 free_before=%u free_after_write=%u free_after_verify=%u",round,mode,index,before,after_write,after_verify))retain();
    }
    if(!context(3)||!frame_probe_guard()||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;ok=1;
done:
    if(mapped){if(!report("FRAME_UNMAP_BEFORE"))retain();rc=sceKernelMunmap(window,FRAME_WINDOW);
        if(!report("FRAME_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        if(!report("FRAME_RELEASE_BEFORE"))retain();rc=sceKernelReleaseDirectMemory(physical,FRAME_WINDOW);
        if(!report("FRAME_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;}
    if(!report("END success=%d nonce=%s Direct_released=%d GPU_calls=0 title_launches=0 model_payload_reads=0 automatic_retry=0",ok,CLOSE_NONCE,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
