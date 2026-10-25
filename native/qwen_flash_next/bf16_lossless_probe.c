/* SPDX-License-Identifier: GPL-3.0-or-later
 * Bounded CPU-only Direct I/O / exact BF16 delivery comparison. No model or GPU.
 */
#include "qualified_context_guard.c"
#include "bf16_lossless_context.h"
#include "bf16_lossless.h"
#ifdef QWEN_PARALLEL_CODEC_PROBE
#include "bf16_decode_probe_io.h"
#endif
#include "hash/sha256/sha256.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#define WINDOW (8u<<20)
#define ALIGNMENT 16384u
#define INPUT_SPACE 3293184u
#ifndef CODEC_ROUNDS
#define CODEC_ROUNDS 6u
#endif
_Static_assert(INPUT_SPACE+QWEN_BF16_MATRIX_MAX+QWEN_BF16_MATRIX_MAX/2<WINDOW,"Bounded codec workspace");
static int pending;
static int pool_started,pool_stopped;
static uint64_t now_ns(void){
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static int headroom(void){
    uint32_t a=0,b=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&a,&minimum,&reserved,&page,&b};
    for(unsigned i=0;i<5;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    const uint32_t extra=reserved>256?reserved:256;
    return page==ALIGNMENT&&minimum&&reserved&&reserved<=minimum&&minimum<=UINT32_MAX-extra&&
        a>=minimum+extra&&b>=minimum+extra&&!sceKernelAvailableFlexibleMemorySize(&flexible)&&flexible>=(264u<<20);
}
static void retain(void){
    (void)report("RETAIN pending=%d no_retry=1 GPU_calls=0",pending);
    for(;;)usleep(1000000);
}
static int unchanged(const struct stat *a,const struct stat *b){
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&
        a->st_gid==b->st_gid&&a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&
        a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int read_exact(int fd,void *target,size_t bytes,uint64_t offset){
    if(!bytes||bytes>INPUT_SPACE||bytes%ALIGNMENT||offset%ALIGNMENT||!headroom())return 0;
    if(!report("READ_BEFORE bytes=%zu",bytes))return 0;
    pending=1;ssize_t got=pread(fd,target,bytes,(off_t)offset);pending=0;
    if(!report("READ_RETURNED bytes=%lld",(long long)got))retain();
    return got==(ssize_t)bytes;
}
static int digest(const void *data,size_t bytes,const unsigned char expected[32]){
    sha256_t h;unsigned char result[32];sha256_init(&h);sha256_update(&h,data,bytes);sha256_final(&h,result);
    return !memcmp(result,expected,32);
}
int main(int argc,char **argv){
    (void)argv;int ok=0,mapped=0,fd=-1,initial_valid=0;int64_t physical=-1;unsigned char *window=NULL;
    struct stat initial={0},current={0};
    output_fd=open(CODEC_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s scratch_bytes=%u samples=%u modes=%u rounds=%u maximum_outstanding_reads=1 GPU_calls=0 title_launches=0",CLOSE_NONCE,WINDOW,CODEC_SAMPLES,CODEC_MODES,CODEC_ROUNDS))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||!headroom()||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("DIRECT_ALLOC_BEFORE bytes=%u",WINDOW))goto done;
    int rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,ALIGNMENT,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();
    if(rc<0){if(physical>=0)retain();goto done;}if(physical<0)retain();
    if(!report("DIRECT_MAP_BEFORE bytes=%u",WINDOW))retain();
    rc=sceKernelMapDirectMemory((void **)&window,WINDOW,3,0,physical,ALIGNMENT);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc)||rc<0||!window||(uintptr_t)window%ALIGNMENT)retain();mapped=1;
    if(seteuid(1)||geteuid()!=1)goto finish;
    fd=open(CODEC_PACK,O_RDONLY|O_DIRECT|O_NOFOLLOW);
    if(fd<0||fstat(fd,&initial)||!S_ISREG(initial.st_mode)||!initial.st_ino||initial.st_size!=(off_t)CODEC_PACK_BYTES||
       (fcntl(fd,F_GETFL)&O_DIRECT)!=O_DIRECT)goto finish;
    initial_valid=1;
    sha256_t hash;sha256_init(&hash);
    for(uint64_t offset=0;offset<CODEC_PACK_BYTES;){
        size_t bytes=CODEC_PACK_BYTES-offset;if(bytes>1u<<20)bytes=1u<<20;
        if(!read_exact(fd,window,bytes,offset))goto finish;sha256_update(&hash,window,bytes);offset+=bytes;
    }
    unsigned char result[32];sha256_final(&hash,result);if(memcmp(result,codec_pack_SHA256,32))goto finish;
    if(!report("EOF_BEFORE"))retain();pending=1;ssize_t tail=pread(fd,window,ALIGNMENT,CODEC_PACK_BYTES);pending=0;
    if(!report("EOF_RETURNED bytes=%lld",(long long)tail))retain();if(tail!=0)goto finish;
    if(fstat(fd,&current)||!unchanged(&initial,&current)||!report("PACK_complete_SHA256_identity_EOF=1"))goto finish;
    unsigned char *output=window+INPUT_SPACE,*scratch=output+QWEN_BF16_MATRIX_MAX;
    for(unsigned i=0;i<65536;++i){window[i]=(unsigned char)(((i>>8)&0x80)|(i&0x7f));scratch[i]=(unsigned char)(i>>7);}
    qwen_bf16_join(window,scratch,65536,output);
    for(unsigned i=0;i<65536;++i)if(output[2*i]!=(unsigned char)i||output[2*i+1]!=(unsigned char)(i>>8))goto finish;
    if(!report("ALL_65536_BF16_patterns_exact=1"))goto finish;
#ifdef QWEN_PARALLEL_CODEC_PROBE
    if(!headroom()||!bf16_probe_start())retain();pool_started=1;
#endif
    const uint64_t started=now_ns();if(!started)goto finish;
    for(unsigned round=0;round<CODEC_ROUNDS;++round)for(unsigned order=0;order<CODEC_MODES;++order){
        const unsigned mode=(round+order)%CODEC_MODES;
        for(unsigned sample=0;sample<CODEC_SAMPLES;++sample){
            if(now_ns()-started>UINT64_C(40000000000)||!headroom())goto finish;
            const struct codec_extent *e=&codec_samples[sample][mode];
            if(!e->bytes||e->bytes>INPUT_SPACE||e->requested>INPUT_SPACE||e->bytes>e->requested||
               e->offset>CODEC_PACK_BYTES||e->requested>CODEC_PACK_BYTES-e->offset||
               (!mode&&(e->bytes!=QWEN_BF16_MATRIX_MAX||e->requested!=QWEN_BF16_MATRIX_MAX)))goto finish;
            unsigned char *target=mode?window:output;
            if(!report("READ_BEFORE sample=%u mode=%u bytes=%u",sample,mode,e->requested))retain();
            const uint64_t a=now_ns();pending=1;ssize_t got=pread(fd,target,e->requested,e->offset);pending=0;const uint64_t b=now_ns();
            if(!report("READ_RETURNED bytes=%lld",(long long)got))retain();
            if(got!=(ssize_t)e->requested||b<a||!a)goto finish;
            uint64_t restore_ns=0;
            if(mode){
                const uint64_t c=now_ns();
                if(qwen_codec_u32(window+8)!=QWEN_BF16_MATRIX_MAX)goto finish;
                int decoded;
#ifdef QWEN_PARALLEL_CODEC_PROBE
                if(mode==3)decoded=bf16_probe_decode(window,e->bytes,output,QWEN_BF16_MATRIX_MAX,scratch,QWEN_BF16_MATRIX_MAX/2);
                else
#endif
                decoded=qwen_bf16_decode(window,e->bytes,output,QWEN_BF16_MATRIX_MAX,scratch,QWEN_BF16_MATRIX_MAX/2);
                if(decoded<0)retain();if(!decoded)goto finish;
                const uint64_t d=now_ns();if(!c||d<c)goto finish;restore_ns=d-c;
                if(!digest(window,e->bytes,e->encoded_sha256))goto finish;
            }
            if(!digest(output,QWEN_BF16_MATRIX_MAX,codec_raw_SHA256[sample])||fstat(fd,&current)||!unchanged(&initial,&current))goto finish;
            if(!report("SAMPLE round=%u mode=%u index=%u read_ns=%llu restore_ns=%llu delivery_ns=%llu physical_bytes=%u exact_SHA256=1",round,mode,sample,
               (unsigned long long)(b-a),(unsigned long long)restore_ns,(unsigned long long)(b-a+restore_ns),e->requested))retain();
        }
    }
    ok=1;
finish:
    if(pending)retain();
#ifdef QWEN_PARALLEL_CODEC_PROBE
    if(pool_started){if(!bf16_probe_stop())retain();pool_stopped=1;}
#endif
    if(fd>=0){if(initial_valid&&(fstat(fd,&current)||!unchanged(&initial,&current)))ok=0;
        if(close(fd))retain();fd=-1;}
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom()||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(pool_started&&!pool_stopped)retain();
    if(mapped){if(!report("DIRECT_UNMAP_BEFORE"))retain();rc=sceKernelMunmap(window,WINDOW);
        if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        if(!report("DIRECT_RELEASE_BEFORE"))retain();rc=sceKernelReleaseDirectMemory(physical,WINDOW);
        if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;window=NULL;}
    if(!report("END success=%d nonce=%s pending_reads=%d Direct_released=%d GPU_calls=0 title_launches=0 automatic_retry=0",ok,CLOSE_NONCE,pending,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
