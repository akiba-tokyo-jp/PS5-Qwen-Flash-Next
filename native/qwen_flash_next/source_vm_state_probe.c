/* SPDX-License-Identifier: GPL-3.0-or-later
 * Read bounded VM counters without model payload, allocation or GPU operations.
 */
#include "qualified_context_guard.c"
#include <fcntl.h>
#include <time.h>
#include "vm_state_context.h"
static uint64_t now(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static int counter(const char *name,unsigned phase) {
    struct {uint64_t first;uint32_t value;uint64_t last;} g={GUARD,0,GUARD};
    size_t bytes=sizeof(g.value);errno=0;
    int rc=sysctlbyname(name,&g.value,&bytes,NULL,0),saved=errno;
    int intact=g.first==GUARD&&g.last==GUARD;
    int available=!rc&&bytes==sizeof(g.value)&&intact;
    return report("VM phase=%u name=%s available=%d rc=%d errno=%d bytes=%zu value=%u canaries=%d",phase,name,available,rc,saved,bytes,available?g.value:0,intact)&&intact;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0;uint64_t begun=0;
    output_fd=open(PROBE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s VM_metadata_only=1 source_payload_reads=0 physical_allocations=0 GPU_calls=0 title_launches=0",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    begun=now();if(!begun)goto done;
    static const char *names[]={"hw.pagesize","vm.stats.vm0.v_page_count","vm.stats.vm0.v_free_count",
        "vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","vm.stats.vm0.v_free_target",
        "vm.stats.vm0.v_free_severe","vm.stats.vm0.v_cache_count","vm.stats.vm0.v_cache_min",
        "vm.stats.vm0.v_inactive_count","vm.stats.vm0.v_inactive_target","vm.stats.vm0.v_active_count",
        "vm.stats.vm0.v_wire_count","vm.stats.vm0.v_pageout_free_min"};
    for(unsigned phase=0;phase<3;++phase) {
        for(unsigned i=0;i<sizeof(names)/sizeof(names[0]);++i)if(!counter(names[i],phase))goto done;
        if(!now()||now()-begun>UINT64_C(5000000000))goto done;
        if(phase<2){const struct timespec pause={0,100000000};if(nanosleep(&pause,NULL))goto done;}
    }
    ok=context(3)&&sceSystemServiceGetAppIdOfRunningBigApp()==-1;
done:
    if(!report("END success=%d nonce=%s worker_active=0 VM_metadata_only=1 source_payload_reads=0 physical_allocations=0 GPU_calls=0 title_launches=0 read_retries=0",ok,CLOSE_NONCE))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
