/* SPDX-License-Identifier: MIT
 * Independent CPU-only native title: no model, GPU, display or worker code.
 * It measures loader/main headroom and one ordinary4KiB libc allocation.
 */
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <time.h>
#include <unistd.h>
#include "sha256.h"
#include "loader_probe_context.h"
extern void qwen_native_stage(const char*);
extern void qwen_native_halt(const char*) __attribute__((noreturn));
static int journal=-1;
static int report(const char*format,...){
    char line[1024];va_list args;va_start(args,format);int n=vsnprintf(line,sizeof(line)-1,format,args);va_end(args);
    if(journal<0||n<0||(size_t)n>=sizeof(line)-1)return 0;
    line[n++]='\n';return write(journal,line,(size_t)n)==n&&!fsync(journal);
}
static int unchanged(const struct stat*a,const struct stat*b){
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_size==b->st_size&&
        a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
        a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
#define QWEN_LAUNCH_WINDOW 65536u
#include "app_named_stat.h"
#define lstat qwen_app_named_stat
#include "launch_integrity_native.h"
#undef lstat
struct vm_values {uint32_t free,inactive,active,wired;};
static int vm(struct vm_values*v){
    uint32_t*values[]={&v->free,&v->inactive,&v->active,&v->wired};
    const char*names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_inactive_count","vm.stats.vm0.v_active_count","vm.stats.vm0.v_wire_count"};
    for(unsigned i=0;i<4;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    return 1;
}
static int fresh(const char*path,const char*text){
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(fd<0)return 0;
    int ok=!fchmod(fd,0644)&&write(fd,text,strlen(text))==(ssize_t)strlen(text)&&!fsync(fd);
    return !close(fd)&&ok;
}
int main(void){
    qwen_native_stage("CPU_loader_footprint_main_entered_GPU_not_started");
    struct vm_values first={0},last={0};struct loader_probe_context context;char path[256],text[1024];
    static _Alignas(16384) char metadata[16384];
    if(!vm(&first))qwen_native_halt("CPU_loader_initial_VM_returned_failure");
    int fd=open("/app0/qwen-runtime/development.json",O_RDONLY|O_NOFOLLOW|O_DIRECT);
    if(fd<0)qwen_native_halt("CPU_loader_context_open_returned_failure");
    struct stat before,after;int ok=!fstat(fd,&before)&&S_ISREG(before.st_mode)&&before.st_size>0&&before.st_size<320;
    ssize_t n=ok?pread(fd,metadata,sizeof(metadata),0):-1;
    ok=ok&&n==before.st_size&&!fstat(fd,&after)&&unchanged(&before,&after);
    int closed=!close(fd);if(!ok||!closed)qwen_native_halt("CPU_loader_context_read_returned_failure");
    metadata[n]=0;
    if(!loader_probe_parse(metadata,(size_t)n,&context))qwen_native_halt("CPU_loader_context_parse_returned_failure");
    snprintf(path,sizeof(path),"/app0/qwen-runtime/plan-%s.json.first.start",context.run);
    snprintf(text,sizeof(text),"{\"schema\":\"ps5-qwen-CPU-loader-start-v1\",\"pid\":%d,\"run_id\":\"%s\",\"SELF_sha256\":\"%s\",\"heap_parameter_bytes\":%llu,\"main_free_pages\":%u,\"GPU_calls\":0,\"model_loads\":0}\n",
        getpid(),context.run,context.sha,context.heap,first.free);
    if(!fresh(path,text))qwen_native_halt("CPU_loader_first_report_returned_failure");
    snprintf(path,sizeof(path),"/app0/qwen-runtime/plan-%s.json.IO",context.run);
    journal=open(path,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    if(journal<0||fchmod(journal,0644))qwen_native_halt("CPU_loader_IO_journal_returned_failure");
    const int exact=qwen_launch_digest_matches("/app0/eboot.bin",(size_t)context.bytes,context.sha);
    void*allocation=malloc(4096);const int allocated=allocation!=NULL;
    if(allocation){for(unsigned i=0;i<4096;++i)((volatile unsigned char*)allocation)[i]=0x39;free(allocation);}
    ok=vm(&last);int IO_closed=!close(journal);journal=-1;
    const int success=exact&&allocated&&ok&&IO_closed;
    snprintf(path,sizeof(path),"/app0/qwen-runtime/plan-%s.json",context.run);
    snprintf(text,sizeof(text),"{\"schema\":\"ps5-qwen-CPU-loader-footprint-v1\",\"completed\":%s,\"pid\":%d,\"run_id\":\"%s\",\"SELF_sha256\":\"%s\",\"heap_parameter_bytes\":%llu,\"SELF_verified\":%s,\"small_libc_allocation_returned\":%s,\"VM_main_free\":%u,\"VM_final_free\":%u,\"VM_main_inactive\":%u,\"VM_final_inactive\":%u,\"VM_main_wired\":%u,\"VM_final_wired\":%u,\"all_CPU_IO_returned\":true,\"GPU_calls\":0,\"model_loads\":0,\"source_workers\":0}\n",
        success?"true":"false",getpid(),context.run,context.sha,context.heap,exact?"true":"false",allocated?"true":"false",
        first.free,last.free,first.inactive,last.inactive,first.wired,last.wired);
    if(!fresh(path,text))qwen_native_halt("CPU_loader_final_report_returned_failure");
    qwen_native_stage("CPU_loader_footprint_returned_GPU_not_started_waiting_for_ordinary_close");
    for(;;)usleep(1000000);
}
