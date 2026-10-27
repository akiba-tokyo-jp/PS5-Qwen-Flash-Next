/* SPDX-License-Identifier: GPL-3.0-or-later
 * Actual original NIR constants and production codec, CPU-only BSS fixture.
 */
#include "qualified_context_guard.c"
#include "driver_table_probe_context.h"
#include <fcntl.h>
#include <time.h>
extern size_t table_probe_count(void),table_probe_raw(void),table_probe_packed(void),table_probe_scratch_peak(void);
extern int table_probe_restore(void);
static uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;}
static int headroom(unsigned extra){uint32_t a=0,b=0,minimum=0,reserved=0,page=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&a,&minimum,&reserved,&page,&b};
    for(unsigned i=0;i<5;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    uint64_t required=(uint64_t)minimum+(reserved>256?reserved:256)+extra;
    return report("HEADROOM free_first=%u free_last=%u required=%llu",a,b,(unsigned long long)required)&&page==16384&&minimum&&reserved&&reserved<=minimum&&a>=required&&b>=required;}
int main(int argc,char **argv){(void)argv;int ok=0;
    output_fd=open(TABLE_PROBE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s manifest_sha256=%s tables=%zu raw_bytes=%zu packed_bytes=%zu GPU_calls=0 title_launches=0",CLOSE_NONCE,TABLE_MANIFEST_SHA,
        table_probe_count(),table_probe_raw(),table_probe_packed()))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||!headroom(512)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(seteuid(1)||geteuid()!=1)goto done;
    if(!report("RESTORE_BEFORE original_hashes_required=1 readonly_protection_required=1"))goto finish;
    uint64_t begin=now();int exact=begin&&table_probe_restore();uint64_t end=now();
    ok=exact&&end>=begin;
    if(!report("RESTORE_RETURNED exact_hashes=%d codec_released=%d readonly_protection=%d elapsed_ns=%llu scratch_peak=%zu",exact,exact,exact,
        (unsigned long long)(end-begin),table_probe_scratch_peak()))ok=0;
finish:
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom(0)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(!report("END success=%d nonce=%s GPU_calls=0 title_launches=0 no_retry=1",ok,CLOSE_NONCE))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;}
