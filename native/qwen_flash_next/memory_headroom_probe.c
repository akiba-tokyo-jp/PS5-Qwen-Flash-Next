/* SPDX-License-Identifier: GPL-3.0-or-later
 * Read-only kernel/Flexible metadata after positive preallocation refusals.
 */
#include "qualified_context_guard.c"
#include "memory_probe_context.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
static int scalar(const char *name,uint32_t *value) {
    size_t size=sizeof(*value);return !sysctlbyname(name,value,&size,NULL,0)&&size==sizeof(*value);
}
int main(int argc,char **argv) {
    (void)argv;int ok=0;uint32_t first=0,last=0,minimum=0,reserved=0,target=0,page=0;
    size_t flexible=0;
    output_fd=open(MEMORY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s allocations=0 payload_reads=0 title_launches=0 GPU_calls=0",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!scalar("vm.stats.vm0.v_free_count",&first)||!scalar("vm.stats.vm0.v_free_min",&minimum)||
       !scalar("vm.stats.vm0.v_free_reserved",&reserved)||!scalar("vm.stats.vm0.v_free_target",&target)||
       !scalar("hw.pagesize",&page)||sceKernelAvailableFlexibleMemorySize(&flexible)||
       !scalar("vm.stats.vm0.v_free_count",&last)||page!=16384||!reserved||reserved>minimum||minimum>=target||target>UINT32_MAX-7168)goto done;
    if(!report("MEMORY free_first=%u free_last=%u minimum=%u reserved=%u target=%u page_bytes=%u flexible_bytes=%zu native_startup_target=%u full_prelaunch_required=%u metadata_only=1",
        first,last,minimum,reserved,target,page,flexible,target,target+7168))goto done;
    if(!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    ok=1;
done:
    if(!report("END success=%d nonce=%s allocations=0 payload_reads=0 title_launches=0 GPU_calls=0 automatic_retry=0",ok,CLOSE_NONCE))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
