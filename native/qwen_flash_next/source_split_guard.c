/* SPDX-License-Identifier: MIT
 * Qualified CPU-only context/Direct guard for one fixed source transaction.
 */
#include "qualified_context_guard.c"
#include "source_split_context.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#include <time.h>

int split_report_line(const char *line) {
    return report("%s",line)&&fsync(output_fd)==0;
}
int split_open_journal(void) {
    output_fd=open(SPLIT_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    return output_fd>=0&&constructors==1&&getuid()==1&&geteuid()==0;
}
int split_context(unsigned phase) {
    return context(phase)&&sceSystemServiceGetAppIdOfRunningBigApp()==-1;
}
int split_headroom(void) {
    uint32_t first=0,last=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&first,&minimum,&reserved,&page,&last};
    for(unsigned i=0;i<5;++i){size_t bytes=4;if(sysctlbyname(names[i],values[i],&bytes,NULL,0)||bytes!=4)return 0;}
    const uint32_t extra=reserved>256?reserved:256;
    const int rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    const int ok=page==16384&&minimum&&minimum<=UINT32_MAX-extra&&first>=minimum+extra&&last>=minimum+extra&&
        !rc&&flexible>=(264u<<20);
    if(!ok)(void)report("HEADROOM admitted=0 first=%u last=%u minimum=%u reserved=%u extra=%u page=%u flexible_rc=%d flexible_bytes=%zu",
        first,last,minimum,reserved,extra,page,rc,flexible);
    return ok;
}
uint64_t split_now_ns(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
int split_close_journal(void) {
    const int fd=output_fd;output_fd=-1;return fsync(fd)==0&&close(fd)==0;
}
