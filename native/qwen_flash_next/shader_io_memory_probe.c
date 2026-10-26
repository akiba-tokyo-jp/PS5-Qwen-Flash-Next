/* SPDX-License-Identifier: GPL-3.0-or-later
 * Isolated CPU control for shader input, hashing and durable stage records.
 * This is not a title-startup, registry, codec or GPU qualification.
 */
#include "qualified_context_guard.c"
#include "shader_io_context.h"
#ifndef SHADER_IO_DIRECT
#define SHADER_IO_DIRECT 0
#endif
#include "kernel_memory_trace.h"
#include "hash/sha256/sha256.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#if SHADER_IO_DIRECT
#include <ps5platform/kernel.h>
#endif
#define WINDOW 49152u
#define CALLS 169u
struct observations { struct qwen_kernel_memory_sample idle,write,flush,returned; };
static struct observations stages[CALLS*2];
static struct qwen_kernel_memory_sample reads[CALLS][3],quiet[6],initial,final;
#if SHADER_IO_DIRECT
static struct qwen_kernel_memory_sample allocated;
#define DIRECT_ALIGNMENT 65536u
#define DIRECT_BYTES (((WINDOW+32768u)+DIRECT_ALIGNMENT-1)&~(DIRECT_ALIGNMENT-1))
static unsigned char *direct_base,*input_data;
static int64_t physical=-1;
static int mapped;
#else
static struct {uint64_t a[2];_Alignas(16384) unsigned char data[WINDOW];uint64_t b[2];} input;
#define input_data input.data
#endif
static unsigned read_calls,returned_calls,stage_count;
static uint64_t returned_bytes;
static int pending;
#if SHADER_IO_DIRECT
static void retain(void) {
    (void)report("RETAIN owned_Direct_backing=1 no_retry=1 GPU_calls=0");
    for(;;)usleep(1000000);
}
#endif
static int canaries(void) {
#if SHADER_IO_DIRECT
    for(unsigned i=0;i<16384;++i)if(direct_base[i]!=0xa7||direct_base[16384+WINDOW+i]!=0xa7)return 0;
    return 1;
#else
    return input.a[0]==GUARD&&input.a[1]==GUARD&&input.b[0]==GUARD&&input.b[1]==GUARD;
#endif
}
static int scalar(void *unused,const char *name,uint32_t *value) {
    (void)unused;size_t n=sizeof(*value);
    return !sysctlbyname(name,value,&n,NULL,0)&&n==sizeof(*value);
}
static uint64_t now(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000||
       (uint64_t)t.tv_sec>UINT64_MAX/1000000000-1)return 0;
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static int sample(struct qwen_kernel_memory_sample *s) {
    return qwen_kernel_memory_observe(NULL,scalar,now(),0,s)&&qwen_kernel_memory_floor(s,256);
}
static int same(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&
        a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&
        a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int marker(int returned) {
    if(stage_count>=CALLS*2)return 0;
    struct observations *s=&stages[stage_count++];
    const struct timespec delay={0,2000000};
    const char *text=returned?"shader_asset_read_native_call_returned\n":"shader_asset_read_before_native_call\n";
    size_t bytes=strlen(text);
    if(!sample(&s->idle)||nanosleep(&delay,NULL)||!sample(&s->write)||
       s->write.monotonic_ns<s->idle.monotonic_ns+UINT64_C(2000000))return 0;
    if(write(output_fd,text,bytes)!=(ssize_t)bytes||!sample(&s->flush)||fsync(output_fd)||!sample(&s->returned))return 0;
    return 1;
}
static int emit(const char *kind,unsigned index,unsigned part,const struct qwen_kernel_memory_sample *s) {
    return report("SAMPLE kind=%s index=%u part=%u ns=%llu free_first=%u free_last=%u active=%u inactive=%u wired=%u cache=%u",
        kind,index,part,(unsigned long long)s->monotonic_ns,s->free_first,s->free_last,s->active,s->inactive,s->wired,s->cache);
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,fd=-1;struct stat before,opened,after;
    sha256_t hash;unsigned char digest[32];char hex[65];uint64_t begun=0;
    output_fd=open(SHADER_IO_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s CPU_only=1 title_launches=0 GPU_calls=0 maximum_reads=%u bytes=%llu input_window=%u matched_idle_ns=2000000 additional_floor_pages=256 static_storage_bytes=%zu",
        CLOSE_NONCE,CALLS,(unsigned long long)SHADER_IO_BYTES,WINDOW,sizeof(stages)+sizeof(reads)+sizeof(quiet)))goto done;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1||!sample(&initial))goto done;
#if SHADER_IO_DIRECT
    {int64_t start=-1;size_t available=0,flexible=0;int64_t pool=sceKernelGetDirectMemorySize();
    int query=pool>0?sceKernelAvailableDirectMemorySize(0,pool,DIRECT_ALIGNMENT,&start,&available):-1;
    int flex=sceKernelAvailableFlexibleMemorySize(&flexible);
    if(!report("DIRECT_BUDGET bytes=%u alignment=%u pool=%lld query_rc=%d start=%lld available=%zu flexible_rc=%d flexible=%zu CPU_type=%d",
        DIRECT_BYTES,DIRECT_ALIGNMENT,(long long)pool,query,(long long)start,available,flex,flexible,PS5_KERNEL_DIRECT_TYPE_CPU)||
       pool<0||(pool>0&&(query||start<0||available<DIRECT_BYTES))||flex||flexible<(1u<<20))goto done;
    /* A zero context value is not claimed as available capacity. The exact
     * CPU control already qualified forwarding this API result to allocation
     * for 8 MiB. This independent arm requests at most 128 KiB, once, and
     * relies on its returned allocation status; title/GPU gates are unchanged.
     */
    if(!report("DIRECT_ALLOC_BEFORE bytes=%u",DIRECT_BYTES))goto done;
    int rc=sceKernelAllocateDirectMemory(0,pool,DIRECT_BYTES,DIRECT_ALIGNMENT,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();
    if(rc){if(physical>=0)retain();goto done;}if(physical<0)retain();
    if(!report("DIRECT_MAP_BEFORE"))retain();
    rc=sceKernelMapDirectMemory((void **)&direct_base,DIRECT_BYTES,3,0,physical,DIRECT_ALIGNMENT);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc)||rc||!direct_base||(uintptr_t)direct_base%DIRECT_ALIGNMENT)retain();mapped=1;
    memset(direct_base,0xa7,DIRECT_BYTES);input_data=direct_base+16384;
    if(!sample(&allocated))goto done;}
#else
    input.a[0]=input.a[1]=input.b[0]=input.b[1]=GUARD;
#endif
    if(lstat(SHADER_IO_PATH,&before)||!S_ISREG(before.st_mode)||before.st_size!=(off_t)SHADER_IO_BYTES)goto done;
    fd=open(SHADER_IO_PATH,O_RDONLY|O_DIRECT|O_NOFOLLOW);
    if(fd<0)goto done;
    int flags=fcntl(fd,F_GETFL);
    if(flags<0||!(flags&O_DIRECT)||fstat(fd,&opened)||!same(&before,&opened))goto done;
    sha256_init(&hash);begun=now();
    if(!begun||!report("READ_SCOPE direct_flag_set=1 static_aligned_window=%u owned_Direct_window=%u tracked_Direct_heap=0 registry_initialized=0 codec_initialized=0",!SHADER_IO_DIRECT,SHADER_IO_DIRECT))goto done;
    for(uint64_t offset=0;offset<SHADER_IO_BYTES;) {
        unsigned i=read_calls;struct stat current;
        uint64_t tick=now();
        if(i>=CALLS||tick<begun||tick-begun>UINT64_C(10000000000)||
           fstat(fd,&current)||!same(&opened,&current)||!marker(0)||!sample(&reads[i][0]))goto done;
        const size_t logical=SHADER_IO_BYTES-offset<WINDOW?(size_t)(SHADER_IO_BYTES-offset):WINDOW;
        pending=1;++read_calls;
        ssize_t got=pread(fd,input_data,WINDOW,(off_t)offset);
        pending=0;++returned_calls;
        if(!sample(&reads[i][1])||got!=(ssize_t)logical||!canaries())goto done;
        sha256_update(&hash,input_data,logical);
        if(!sample(&reads[i][2])||!marker(1)||fstat(fd,&current)||!same(&opened,&current))goto done;
        returned_bytes+=logical;offset+=logical;
    }
    sha256_final(&hash,digest);
    for(unsigned i=0;i<32;++i)snprintf(hex+2*i,3,"%02x",digest[i]);
    if(strcmp(hex,SHADER_IO_SHA256)||read_calls!=CALLS||returned_calls!=CALLS||returned_bytes!=SHADER_IO_BYTES||
       fstat(fd,&after)||!same(&opened,&after)||lstat(SHADER_IO_PATH,&after)||!same(&opened,&after))goto done;
    {int closed=close(fd);fd=-1;if(closed)goto done;}
    /* No filesystem writes occur inside this completed-read quiet interval. */
    for(unsigned i=0;i<6;++i) {
        if(i){const struct timespec delay={0,200000000};if(nanosleep(&delay,NULL))goto done;}
        if(!sample(&quiet[i]))goto done;
    }
    if(!sample(&final)||!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!emit("initial",0,0,&initial))goto done;
#if SHADER_IO_DIRECT
    if(!emit("allocation",0,0,&allocated))goto done;
#endif
    for(unsigned i=0;i<stage_count;++i) {
        if(!emit("stage",i,0,&stages[i].idle)||!emit("stage",i,1,&stages[i].write)||
           !emit("stage",i,2,&stages[i].flush)||!emit("stage",i,3,&stages[i].returned))goto done;
    }
    for(unsigned i=0;i<read_calls;++i)for(unsigned j=0;j<3;++j)if(!emit("read",i,j,&reads[i][j]))goto done;
    for(unsigned i=0;i<6;++i)if(!emit("quiet",i,0,&quiet[i]))goto done;
    if(!emit("final",0,0,&final))goto done;
    ok=1;
done:
    if(fd>=0&&!pending&&close(fd))ok=0;
#if SHADER_IO_DIRECT
    if(pending)retain();
    if(mapped) {
        if(!canaries())ok=0;
        if(!report("DIRECT_UNMAP_BEFORE"))retain();int rc=sceKernelMunmap(direct_base,DIRECT_BYTES);
        if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();mapped=0;
    }
    if(physical>=0) {
        if(!report("DIRECT_RELEASE_BEFORE"))retain();int rc=sceKernelReleaseDirectMemory(physical,DIRECT_BYTES);
        if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;direct_base=input_data=NULL;
    }
    if(!report("DIRECT_OWNERSHIP released=%d pending=%d",physical<0&&!mapped,pending))ok=0;
#endif
    if(!report("END success=%d nonce=%s reads=%u returned=%u bytes=%llu stages=%u pending=%d whole_SHA256=%d title_launches=0 GPU_calls=0 automatic_retry=0",
        ok,CLOSE_NONCE,read_calls,returned_calls,(unsigned long long)returned_bytes,stage_count,pending,ok))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;
    return ok?0:1;
}
