/* SPDX-License-Identifier: GPL-3.0-or-later
 * Qualified CPU-only wrapper around the application's actual virtual provider.
 */
#include "qualified_context_guard.c"
#include <fcntl.h>
#include <time.h>
#include <ps5platform/kernel.h>
#include "virtual_charge_context.h"
static unsigned stage_calls,measurements,skipped;
static int scalar(const char *name,uint32_t *value) {
    struct {uint64_t a;uint32_t value;uint64_t b;} g={GUARD,0,GUARD};size_t bytes=4;
    if(sysctlbyname(name,&g.value,&bytes,NULL,0)||bytes!=4||g.a!=GUARD||g.b!=GUARD)return 0;
    *value=g.value;return 1;
}
void qwen_native_stage(const char *unused) {(void)unused;++stage_calls;}
int virtual_charge_checkpoint(const char *label,unsigned index,uint64_t bytes,unsigned predict) {
    uint32_t free1=0,free2=0,minimum=0,reserved=0,page=0,target=0;
    if(!scalar("vm.stats.vm0.v_free_count",&free1)||!scalar("vm.stats.vm0.v_free_min",&minimum)||
       !scalar("vm.stats.vm0.v_free_reserved",&reserved)||!scalar("hw.pagesize",&page)||
       !scalar("vm.stats.vm0.v_free_target",&target)||!scalar("vm.stats.vm0.v_free_count",&free2)||
       page!=16384||!reserved||reserved>minimum||minimum>=target)return 0;
    uint64_t extra=reserved>256?reserved:256;
    /* Conservative pre-allocation estimate:32pages/GiB plus256pages, above
     * the observed whole-rehearsal drop. Never count inactive pages as free. */
    uint64_t prediction=predict?((bytes+((UINT64_C(1)<<30)-1))>>30)*32+256:0;
    uint64_t required=minimum+extra+prediction;
    int admitted=free1>=required&&free2>=required;
    if(!strcmp(label,"skipped_capacity"))++skipped;
    if(!report("VIRTUAL_CHARGE label=%s index=%u bytes=%llu free_first=%u free_last=%u minimum=%u reserved=%u target=%u page=%u required=%llu admitted=%d stage_calls=%u observation=%u",label,index,(unsigned long long)bytes,free1,free2,minimum,reserved,target,page,(unsigned long long)required,admitted,stage_calls,measurements++))return 0;
    return predict?admitted:1;
}
int virtual_charge_pause(void) {return !usleep(100000);}
int virtual_charge_run(void);
int main(int argc,char **argv) {
    (void)argv;int ok=0;
    output_fd=open(PROBE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s actual_virtual_provider=1 physical_allocations=0 source_payload_reads=0 GPU_calls=0 title_launches=0",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    ok=virtual_charge_run();
    if(!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(!report("END success=%d nonce=%s worker_active=0 observations=%u skipped=%u physical_allocations=0 source_payload_reads=0 GPU_calls=0 title_launches=0 reservation_retries=0",ok,CLOSE_NONCE,measurements,skipped))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;
    return ok?0:1;
}
