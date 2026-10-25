/* SPDX-License-Identifier: GPL-3.0-or-later
 * Inspect only owned file residency through non-accessible private windows.
 * No payload dereference/read, physical allocation, cache advice, or GPU calls.
 */
#include "qualified_context_guard.c"
#include "file_residency_context.h"
#include "file_residency.h"
#include "kernel_memory_trace.h"
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
static unsigned file_index;
static int source_fd=-1,api_rc,api_error;
static uint64_t begun_ns;
static struct qwen_file_residency state;
static int scalar(void*unused,const char*name,uint32_t*value){(void)unused;size_t n=4;return !sysctlbyname(name,value,&n,NULL,0)&&n==4;}
static int memory(void*unused){
    (void)unused;struct timespec t;struct qwen_kernel_memory_sample s;
    if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000||
       (uint64_t)t.tv_sec>UINT64_MAX/1000000000-1||
       !qwen_kernel_memory_observe(NULL,scalar,(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec,0,&s))return 0;
    uint64_t now=(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
    if(!begun_ns)begun_ns=now;
    if(now<begun_ns||now-begun_ns>UINT64_C(20000000000))return 0;
    return report("MEMORY file=%u free_first=%u free_last=%u inactive=%u wired=%u minimum=%u reserved=%u target=%u page_bytes=%u",
        file_index,s.free_first,s.free_last,s.inactive,s.wired,s.minimum,s.reserved,s.target,s.page_bytes)&&qwen_kernel_memory_floor(&s,64);
}
static int marker(void*unused,unsigned phase,unsigned edge){(void)unused;
    return report("RESIDENCY_CALL file=%u phase=%u edge=%u rc=%d errno=%d",file_index,phase,edge,edge?api_rc:0,edge?api_error:0)&&!fsync(output_fd);}
static void*map_none(void*unused,uint64_t offset,size_t bytes){(void)unused;errno=0;void*p=mmap(NULL,bytes,PROT_NONE,MAP_PRIVATE,source_fd,(off_t)offset);api_error=errno;api_rc=p==MAP_FAILED?-1:0;return p;}
static int query(void*unused,const void*p,size_t bytes,char*vec){(void)unused;errno=0;api_rc=mincore(p,bytes,vec);api_error=errno;return api_rc;}
static int release(void*unused,void*p,size_t bytes){(void)unused;errno=0;api_rc=munmap(p,bytes);api_error=errno;return api_rc;}
static int same(const struct stat*a,const struct stat*b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_nlink==b->st_nlink&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;}
int main(int argc,char**argv){
    (void)argv;int ok=0;unsigned completed=0;
    output_fd=open(RESIDENCY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s PROT_NONE_only=1 source_payload_reads=0 cache_advice_calls=0 GPU_calls=0 title_launches=0",CLOSE_NONCE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    for(file_index=0;file_index<sizeof(residency_sources)/sizeof(residency_sources[0]);++file_index){
        const struct residency_source*source=&residency_sources[file_index];struct stat path,opened,after;
        if(!source->inspect_bytes||source->inspect_bytes>source->bytes||lstat(source->path,&path)||!S_ISREG(path.st_mode)||path.st_size!=(off_t)source->bytes||path.st_nlink!=1)goto done;
        source_fd=open(source->path,O_RDONLY|O_NOFOLLOW);if(source_fd<0)goto done;
        if(fstat(source_fd,&opened)||!same(&path,&opened))goto done;
        state=(struct qwen_file_residency){0};const struct qwen_file_residency_ops o={NULL,memory,marker,map_none,query,release};
        int scanned=qwen_file_residency_scan(&o,source->inspect_bytes,source->maximum_windows,&state);
        if(!report("FILE_RESIDENCY index=%u scanned=%d pages=%u resident=%u modified=%u referenced=%u maps=%u queries=%u unmaps=%u pending=%u live=%u unsupported=%u",
            file_index,scanned,state.pages,state.resident,state.modified,state.referenced,state.maps,state.queries,state.unmaps,state.pending,state.live,state.unsupported))goto done;
        if(!scanned||state.pending||state.live||fstat(source_fd,&after)||!same(&opened,&after)||lstat(source->path,&after)||!same(&opened,&after))goto done;
        int closed=close(source_fd);source_fd=-1;if(closed)goto done;++completed;
    }
    ok=context(3)&&sceSystemServiceGetAppIdOfRunningBigApp()==-1&&memory(NULL);
done:
    if(source_fd>=0&&!state.pending&&!state.live){if(close(source_fd))ok=0;source_fd=-1;}
    if(!report("END success=%d nonce=%s files_completed=%u pending=%u live=%u source_payload_reads=0 cache_advice_calls=0 GPU_calls=0 title_launches=0 retries=0",ok,CLOSE_NONCE,completed,state.pending,state.live))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
