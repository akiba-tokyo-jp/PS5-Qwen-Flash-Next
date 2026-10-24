/* SPDX-License-Identifier: GPL-3.0-or-later
 * Separate sealed-file metadata from durable stage-journal write costs.
 */
#include "qualified_context_guard.c"
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#include "journal_charge_context.h"
static int observed_free(uint32_t *free_pages) {
    uint32_t minimum=0,reserved=0,page=0;size_t bytes=4;
    if(sysctlbyname("vm.stats.vm0.v_free_count",free_pages,&bytes,NULL,0)||bytes!=4)return 0;
    bytes=4;if(sysctlbyname("vm.stats.vm0.v_free_min",&minimum,&bytes,NULL,0)||bytes!=4)return 0;
    bytes=4;if(sysctlbyname("vm.stats.vm0.v_free_reserved",&reserved,&bytes,NULL,0)||bytes!=4)return 0;
    bytes=4;if(sysctlbyname("hw.pagesize",&page,&bytes,NULL,0)||bytes!=4||page!=16384||!reserved||reserved>minimum)return 0;
    return *free_pages>=minimum+(reserved>256?reserved:256)+128;
}
static uint64_t now(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0)return 0;
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,stopped=0;unsigned completed=0;uint64_t started=0;
    output_fd=open(PROBE_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s metadata_and_journal_only=1 GPU_calls=0 source_payload_reads=0 title_launches=0",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    started=now();if(!started)goto done;
    uint32_t first=0,last=0;if(!observed_free(&first))goto done;
    for(unsigned i=0;i<sizeof(metadata_files)/sizeof(metadata_files[0]);++i) {
        if(!observed_free(&last)){stopped=1;break;}
        int fd=open(metadata_files[i].path,O_RDONLY|O_NOFOLLOW);if(fd<0)goto done;
        struct stat s;int valid=!fstat(fd,&s)&&S_ISREG(s.st_mode)&&s.st_size>0&&(uint64_t)s.st_size==metadata_files[i].bytes;
        if(close(fd)||!valid)goto done;++completed;
    }
    (void)observed_free(&last);
    if(!report("METADATA files=%u free_before=%u free_after=%u source_payload_reads=0",completed,first,last))goto done;
    for(unsigned group=0;group<12&&!stopped;++group) {
        if(!observed_free(&first)){stopped=1;break;}
        char path[240];int n=snprintf(path,sizeof(path),"%s-%u.log",JOURNAL_PREFIX,group);if(n<=0||(size_t)n>=sizeof(path))goto done;
        int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(fd<0)goto done;
        unsigned lines=0;uint64_t begin=now();int io_ok=begin>0;
        static const char line[]="model_mapping_before_virtual_source_reserve mapped_files=48 unmapped_files=0 GPU_not_started=1 model_loaded=0\n";
        for(;io_ok&&lines<96;++lines) {
            if(!observed_free(&last)||now()-started>UINT64_C(40000000000)){stopped=1;break;}
            if(group%3==1)io_ok=write(fd,line,sizeof(line)-2)==sizeof(line)-2&&write(fd,"\n",1)==1;
            else io_ok=write(fd,line,sizeof(line)-1)==sizeof(line)-1;
            if(io_ok&&group%3!=0)io_ok=!fsync(fd);
        }
        uint64_t end=now();if(close(fd)||!io_ok||end<begin)goto done;
        (void)observed_free(&last);
        if(!report("JOURNAL group=%u mode=%u completed_lines=%u bytes_per_line=%zu fsync_per_line=%d writes_per_line=%u free_before=%u free_after=%u elapsed_ns=%llu completed_boundary_stop=%d",group,group%3,lines,sizeof(line)-1,group%3!=0,group%3==1?2:1,first,last,(unsigned long long)(end-begin),stopped))goto done;
    }
    ok=context(3)&&sceSystemServiceGetAppIdOfRunningBigApp()==-1;
done:
    if(!report("END success=%d nonce=%s worker_active=0 stopped_at_completed_boundary=%d metadata_files=%u source_payload_reads=0 GPU_calls=0 title_launches=0 read_retries=0",ok,CLOSE_NONCE,stopped,completed))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;
    return ok?0:1;
}
