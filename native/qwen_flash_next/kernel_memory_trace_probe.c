/* SPDX-License-Identifier: GPL-3.0-or-later
 * Finite CPU-only memory-category trace and exact canonical Direct digest.
 */
#include "qualified_context_guard.c"
#include "memory_trace_context.h"
#include "kernel_memory_trace.h"
#include "launch_integrity.h"
#include "hash/sha256/sha256.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#ifndef MEMORY_NETWORK_CONTROL
#define MEMORY_NETWORK_CONTROL 0
#endif
#ifndef MEMORY_TRACE_CAPACITY
#define MEMORY_TRACE_CAPACITY 64
#endif
#ifndef MEMORY_NETWORK_STEP_NS
#define MEMORY_NETWORK_STEP_NS 250000000
#endif

enum {TRACE_CAPACITY=MEMORY_TRACE_CAPACITY,WINDOW_BYTES=1048576};
_Static_assert(TRACE_CAPACITY==64||TRACE_CAPACITY==128,"Finite metadata trace profiles");
static struct qwen_kernel_memory_sample samples[TRACE_CAPACITY];
static unsigned sample_count;
static _Alignas(16384) unsigned char input_window[WINDOW_BYTES];
static uint64_t started_ns;
static uint64_t now_ns(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||
       t.tv_nsec>=1000000000||(uint64_t)t.tv_sec>UINT64_MAX/1000000000-1)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static int scalar(void *unused,const char *name,uint32_t *value) {
    (void)unused;
    struct {uint64_t a;uint32_t value;uint64_t b;} g={GUARD,0,GUARD};
    size_t bytes=sizeof(g.value);
    if(sysctlbyname(name,&g.value,&bytes,NULL,0)||bytes!=sizeof(g.value)||
       g.a!=GUARD||g.b!=GUARD)return 0;
    *value=g.value;return 1;
}
static int sample(unsigned phase) {
    const uint64_t current=now_ns();
    if(sample_count==TRACE_CAPACITY||!started_ns||current<started_ns||
       current-started_ns>UINT64_C(20000000000))return 0;
    if(!qwen_kernel_memory_observe(NULL,scalar,current,phase,samples+sample_count))return 0;
    ++sample_count;return 1;
}
static int idle(unsigned phase) {
    for(unsigned i=0;i<5;++i) {
        if(!sample(phase))return 0;
        if(i<4){const struct timespec delay={0,250000000};if(nanosleep(&delay,NULL))return 0;}
    }
    return 1;
}
static int network_control(void) {
    if(!sample(5))return 0;
    const uint64_t file_pages=(MEMORY_CANONICAL_BYTES+16383)/16384;
    if(file_pages>UINT32_MAX-64||!qwen_kernel_memory_floor(samples+sample_count-1,(uint32_t)file_pages+64))
        return report("NETWORK_REFUSED payload_reads=0")&&0;
    if(!report("NETWORK_WINDOW admitted=1 maximum_bytes=%llu duration_ms=%u",(unsigned long long)MEMORY_CANONICAL_BYTES,(unsigned)(16ull*MEMORY_NETWORK_STEP_NS/1000000)))return 0;
    for(unsigned i=0;i<16;++i) {
        const struct timespec delay={0,MEMORY_NETWORK_STEP_NS};
        if(nanosleep(&delay,NULL)||!sample(5))return 0;
        if(!qwen_kernel_memory_floor(samples+sample_count-1,0))return 0;
    }
    return report("NETWORK_WINDOW_ENDED");
}
static int same_file(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&
        a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&a->st_size==b->st_size&&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
        a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
struct digest_context {int fd;sha256_t hash;uint64_t offset;size_t requested;int64_t returned;};
static uint64_t digest_now(void *unused){(void)unused;return now_ns();}
static int digest_headroom(void *unused) {
    (void)unused;return sample(2)&&qwen_kernel_memory_floor(samples+sample_count-1,0);
}
static int digest_marker(void *context,int before) {
    struct digest_context *c=context;
    if(before)return report("READ_BEFORE");
    return report("READ_RETURNED offset=%llu requested=%zu bytes=%lld",
        (unsigned long long)c->offset,c->requested,(long long)c->returned);
}
static int64_t digest_read(void *context,void *window,size_t bytes,uint64_t offset) {
    struct digest_context *c=context;c->offset=offset;c->requested=bytes;
    return c->returned=pread(c->fd,window,bytes,(off_t)offset);
}
static int digest_consume(void *context,const unsigned char *data,size_t bytes) {
    struct digest_context *c=context;sha256_update(&c->hash,data,bytes);return 1;
}
static int direct_digest(void) {
    if(!sample(1)||!qwen_kernel_memory_floor(samples+sample_count-1,WINDOW_BYTES/16384))
        return report("DIRECT_REFUSED allocations=0 payload_reads=0")&&0;
    struct stat path={0},opened={0},after={0};int fd=-1,ok=0;
    if(lstat(MEMORY_CANONICAL,&path)||!S_ISREG(path.st_mode)||
       path.st_size!=(off_t)MEMORY_CANONICAL_BYTES)return 0;
    fd=open(MEMORY_CANONICAL,O_RDONLY|O_DIRECT|O_NOFOLLOW);
    if(fd<0)return 0;
    const int flags=fcntl(fd,F_GETFL);
    if(flags<0||(flags&O_DIRECT)!=O_DIRECT||fstat(fd,&opened)||!same_file(&path,&opened))goto done;
    if(!report("DIRECT_OPEN bytes=%llu window=%u direct_flag_set=1",(unsigned long long)MEMORY_CANONICAL_BYTES,WINDOW_BYTES))goto done;
    struct digest_context c={.fd=fd};sha256_init(&c.hash);
    struct qwen_launch_integrity stream={0};stream.context=&c;
    stream.now_ns=digest_now;stream.headroom=digest_headroom;stream.marker=digest_marker;
    stream.read_at=digest_read;stream.consume=digest_consume;
    if(!qwen_launch_integrity_stream(&stream,input_window,MEMORY_CANONICAL_BYTES,15))goto done;
    unsigned char digest[32];sha256_final(&c.hash,digest);
    if(memcmp(digest,memory_canonical_SHA256,32)||fstat(fd,&after)||!same_file(&opened,&after)||
       lstat(MEMORY_CANONICAL,&after)||!same_file(&opened,&after))goto done;
    ok=report("DIRECT_EXACT bytes=%llu calls=%llu returned=%llu complete_SHA256_identity_EOF=1",
        (unsigned long long)stream.bytes,(unsigned long long)stream.calls,(unsigned long long)stream.returned);
done:
    if(close(fd))ok=0;
    if(!report("FILE_CLOSED success=%d",ok))ok=0;
    return ok;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0;
    output_fd=open(MEMORY_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s trace_capacity=%u window=%u direct_mode=%u explicit_allocations=0 title_launches=0 GPU_calls=0",CLOSE_NONCE,TRACE_CAPACITY,WINDOW_BYTES,MEMORY_DIRECT_MODE))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    started_ns=now_ns();if(!started_ns||!idle(0))goto done;
    if(MEMORY_NETWORK_CONTROL&&!network_control())goto done;
    if(MEMORY_DIRECT_MODE&&!direct_digest())goto done;
    if(!idle(4)||!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    ok=1;
done:
    for(unsigned i=0;i<sample_count;++i) {
        const struct qwen_kernel_memory_sample *s=samples+i;
        if(!report("SAMPLE seq=%u phase=%u ns=%llu free_first=%u free_last=%u total=%u minimum=%u reserved=%u target=%u active=%u inactive=%u wired=%u cache=%u page_bytes=%u",i,s->phase,(unsigned long long)s->monotonic_ns,s->free_first,s->free_last,s->total,s->minimum,s->reserved,s->target,s->active,s->inactive,s->wired,s->cache,s->page_bytes))ok=0;
    }
    if(!report("END success=%d nonce=%s samples=%u explicit_allocations=0 title_launches=0 GPU_calls=0 automatic_retry=0",ok,CLOSE_NONCE,sample_count))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;
    return ok?0:1;
}
