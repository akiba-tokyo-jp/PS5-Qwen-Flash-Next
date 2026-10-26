/* SPDX-License-Identifier: GPL-3.0-or-later
 * Inspect fixed owned retained SELF prefixes, then verify resident prefixes
 * through two returned Direct reads. No whole-file integrity or reclaim API.
 */
#include "qualified_context_guard.c"
#include "closed_SELF_prefix_context.h"
#include "file_residency.h"
#include "kernel_memory_trace.h"
#include "hash/sha256/sha256.h"
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#define PREFIX_BYTES 1048576u
#ifndef CLOSED_SELF_WHOLE
#define CLOSED_SELF_WHOLE 0
#endif
static _Alignas(16384) unsigned char window[PREFIX_BYTES];
static int fd=-1,pending,api_rc,api_error;
static unsigned completed,selected,reads,returned;
#if CLOSED_SELF_WHOLE
static int status_fd=-1;
static int status(int done,int ok) {
    char line[512];memset(line,' ',sizeof(line));
    int n=snprintf(line,sizeof(line),"PROGRESS nonce=%s last_completed_files=%u selected=%u returned_reads=%u\n",CLOSE_NONCE,completed,selected,returned);
    if(n<0||(size_t)n>=sizeof(line)-200)return 0;
    if(done)n+=snprintf(line+n,sizeof(line)-(size_t)n,"END success=%d nonce=%s pending=%d live_mapping=0 GPU_calls=0 title_launches=0\n",ok,CLOSE_NONCE,pending);
    if(n<0||(size_t)n>=sizeof(line))return 0;
    line[n]=' ';line[sizeof(line)-1]='\n';
    return pwrite(status_fd,line,sizeof(line),0)==sizeof(line)&&!fsync(status_fd);
}
#endif
static uint64_t begun;
static int scalar(void *unused,const char *name,uint32_t *value) {
    (void)unused;size_t n=4;return !sysctlbyname(name,value,&n,NULL,0)&&n==4;
}
static uint64_t now(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000||
       (uint64_t)t.tv_sec>UINT64_MAX/1000000000-1)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static int memory(struct qwen_kernel_memory_sample *s) {
    uint64_t tick=now();
    const uint64_t limit=CLOSED_SELF_WHOLE?UINT64_C(300000000000):UINT64_C(30000000000);
    if(!tick||tick<begun){(void)report("ADMISSION_REFUSAL reason=clock");return 0;}
    if(tick-begun>limit){(void)report("ADMISSION_REFUSAL reason=deadline elapsed_ns=%llu",(unsigned long long)(tick-begun));return 0;}
    if(!qwen_kernel_memory_observe(NULL,scalar,tick,0,s)){(void)report("ADMISSION_REFUSAL reason=counter");return 0;}
    if(!qwen_kernel_memory_floor(s,128)){
        (void)report("ADMISSION_REFUSAL reason=floor free_first=%u free_last=%u minimum=%u reserved=%u additional=128",s->free_first,s->free_last,s->minimum,s->reserved);return 0;
    }
    return 1;
}
static int admit(void *unused){(void)unused;struct qwen_kernel_memory_sample s;return memory(&s);}
static int mark(void *unused,unsigned phase,unsigned edge) {
    (void)unused;
    return report("RESIDENCY_CALL index=%u phase=%u edge=%u rc=%d errno=%d",completed,phase,edge,edge?api_rc:0,edge?api_error:0)&&!fsync(output_fd);
}
static void *map_none(void *unused,uint64_t offset,size_t bytes) {
    (void)unused;errno=0;void *p=mmap(NULL,bytes,PROT_NONE,MAP_PRIVATE,fd,(off_t)offset);api_error=errno;api_rc=p==MAP_FAILED?-1:0;return p;
}
static int query(void *unused,const void *p,size_t bytes,char *vec) {
    (void)unused;errno=0;api_rc=mincore(p,bytes,vec);api_error=errno;return api_rc;
}
static int unmap(void *unused,void *p,size_t bytes) {
    (void)unused;errno=0;api_rc=munmap(p,bytes);api_error=errno;return api_rc;
}
static int same(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_nlink==b->st_nlink&&a->st_uid==b->st_uid&&
        a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
        a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static void retain(void) {
    (void)report("RETAIN pending_or_live_mapping=1 no_retry=1 GPU_calls=0");
    for(;;)usleep(1000000);
}
int main(int argc,char **argv) {
    (void)argv;int ok=0;struct qwen_file_residency resident={0};
    struct qwen_kernel_memory_sample initial,final;
    output_fd=open(PREFIX_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;begun=now();
#if CLOSED_SELF_WHOLE
    status_fd=open(PREFIX_STATUS,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
    if(status_fd<0||!status(0,0))return 2;
#endif
    if(!report("BEGIN nonce=%s CPU_only=1 sources=%zu maximum_prefix_bytes=%u whole_current_file_mode=%u cache_advice_calls=0 title_launches=0 GPU_calls=0 additional_floor_pages=128",CLOSE_NONCE,
        sizeof(prefix_sources)/sizeof(prefix_sources[0]),PREFIX_BYTES,CLOSED_SELF_WHOLE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1||!memory(&initial))goto done;
    for(unsigned i=0;i<sizeof(prefix_sources)/sizeof(prefix_sources[0]);++i) {
        const struct prefix_source *source=&prefix_sources[i];struct stat before,opened,after;
        struct qwen_kernel_memory_sample a,b;
#if !CLOSED_SELF_WHOLE
        unsigned char hashes[2][32];
#endif
        if(!report("PREFIX_FILE_BEFORE index=%u",i)||fsync(output_fd))goto done;
        if(!memory(&a)||lstat(source->path,&before)||!S_ISREG(before.st_mode)||before.st_nlink!=1||before.st_size!=(off_t)source->bytes||source->bytes<PREFIX_BYTES)goto done;
        fd=open(source->path,O_RDONLY|O_DIRECT|O_NOFOLLOW);
        if(fd<0||fstat(fd,&opened)||!same(&before,&opened)||(fcntl(fd,F_GETFL)&O_DIRECT)!=O_DIRECT)goto done;
        resident=(struct qwen_file_residency){0};
        const struct qwen_file_residency_ops ops={NULL,admit,mark,map_none,query,unmap};
        const uint64_t inspect=CLOSED_SELF_WHOLE?source->bytes:PREFIX_BYTES;
        const unsigned windows=(unsigned)((inspect+PREFIX_BYTES-1)/PREFIX_BYTES);
        if(!qwen_file_residency_scan(&ops,inspect,windows,&resident)||resident.pending||resident.live)goto done;
        if(resident.resident) {
            ++selected;
#if CLOSED_SELF_WHOLE
            sha256_t hash;sha256_init(&hash);uint64_t hashed=0;
            for(uint64_t offset=0;offset<source->bytes;) {
                const size_t logical=source->bytes-offset<PREFIX_BYTES?(size_t)(source->bytes-offset):PREFIX_BYTES;
                if(!admit(NULL)||!report("WHOLE_READ_BEFORE index=%u offset=%llu requested=%u logical=%zu",i,(unsigned long long)offset,PREFIX_BYTES,logical)||fsync(output_fd))goto done;
                pending=1;++reads;ssize_t got=pread(fd,window,PREFIX_BYTES,(off_t)offset);pending=0;++returned;
                if(!report("WHOLE_READ_RETURNED index=%u offset=%llu bytes=%lld",i,(unsigned long long)offset,(long long)got)||fsync(output_fd)||got!=(ssize_t)logical)goto done;
                sha256_update(&hash,window,logical);hashed+=logical;offset+=logical;
            }
            const uint64_t eof=source->bytes&~UINT64_C(16383);const size_t tail=(size_t)(source->bytes-eof);
            if(!admit(NULL)||!report("WHOLE_EOF_BEFORE index=%u offset=%llu expected=%zu",i,(unsigned long long)eof,tail)||fsync(output_fd))goto done;
            pending=1;++reads;ssize_t got=pread(fd,window,16384,(off_t)eof);pending=0;++returned;
            if(!report("WHOLE_EOF_RETURNED index=%u bytes=%lld",i,(long long)got)||fsync(output_fd)||got!=(ssize_t)tail)goto done;
            unsigned char digest[32];char hex[65];sha256_final(&hash,digest);
            for(unsigned j=0;j<32;++j)snprintf(hex+2*j,3,"%02x",digest[j]);
            if(hashed!=source->bytes||!report("FILE_CURRENT_DIGEST index=%u bytes=%llu SHA256=%s compared_to_original=0",i,(unsigned long long)hashed,hex))goto done;
#else
            for(unsigned arm=0;arm<2;++arm) {
                if(!admit(NULL)||!report("PREFIX_READ_BEFORE index=%u arm=%u bytes=%u",i,arm,PREFIX_BYTES)||fsync(output_fd))goto done;
                pending=1;++reads;ssize_t got=pread(fd,window,PREFIX_BYTES,0);pending=0;++returned;
                if(!report("PREFIX_READ_RETURNED index=%u arm=%u bytes=%lld",i,arm,(long long)got)||fsync(output_fd)||got!=PREFIX_BYTES)goto done;
                /* Historical native containers have different headers. This
                 * control verifies stable owned bytes, never their format. */
                sha256_t hash;sha256_init(&hash);sha256_update(&hash,window,PREFIX_BYTES);sha256_final(&hash,hashes[arm]);
            }
            if(memcmp(hashes[0],hashes[1],32))goto done;
#endif
        }
        if(fstat(fd,&after)||!same(&opened,&after)||lstat(source->path,&after)||!same(&opened,&after))goto done;
        {int closed=close(fd);fd=-1;if(closed)goto done;}
        if(!memory(&b)||!report("PREFIX_COMPLETE index=%u resident_before=%u free_before=%u free_after=%u inactive_before=%u inactive_after=%u wired_before=%u wired_after=%u prefix_SHA256_twice_equal=%d source_payload_mutations=0",
            i,resident.resident,a.free_last,b.free_last,a.inactive,b.inactive,a.wired,b.wired,!CLOSED_SELF_WHOLE&&resident.resident!=0))goto done;
        ++completed;
#if CLOSED_SELF_WHOLE
        if(!status(0,0))goto done;
#endif
    }
    if(!memory(&final)||!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("SUMMARY free_before=%u free_after=%u inactive_before=%u inactive_after=%u wired_before=%u wired_after=%u",
        initial.free_last,final.free_last,initial.inactive,final.inactive,initial.wired,final.wired))goto done;
    ok=1;
done:
    if(pending||resident.pending||resident.live)retain();
    if(fd>=0){if(close(fd))ok=0;fd=-1;}
    if(!report("END success=%d nonce=%s files_completed=%u selected=%u reads=%u returned=%u pending=%d live_mapping=%u whole_file_integrity_claimed=0 cache_advice_calls=0 title_launches=0 GPU_calls=0 automatic_retries=0",
        ok,CLOSE_NONCE,completed,selected,reads,returned,pending,resident.live))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;
#if CLOSED_SELF_WHOLE
    if(!status(1,ok)||close(status_fd))ok=0;
#endif
    return ok?0:1;
}
