/* SPDX-License-Identifier: GPL-3.0-or-later
 * Read-only comparison against actual sealed role-major physical model parts.
 */
#include "qualified_context_guard.c"
#include "vector_layout_context.h"
#include "vector_layout_delivery.h"
#include "hash/sha256/sha256.h"
#include <ps5platform/kernel.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>
#define PAGE 16384u
#define STRIDE 3293184u
#define MATRIX 3276800u
#define SCRATCH (1u<<20)
#define WINDOW (24u<<20)
static int pending,worker_started,worker_stopped;
static int descriptors[7]={-1,-1,-1,-1,-1,-1,-1};
static struct stat identities[7];
static int identity(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_mode==b->st_mode&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&
        a->st_size==b->st_size&&a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
        a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
}
static int sealed(const struct stat *s,const uint64_t expected[10]) {
    return s->st_dev==expected[0]&&s->st_ino==expected[1]&&s->st_mode==expected[2]&&s->st_uid==expected[3]&&s->st_gid==expected[4]&&
        s->st_size==(off_t)expected[5]&&s->st_mtim.tv_sec==(int64_t)expected[6]&&s->st_mtim.tv_nsec==(int64_t)expected[7]&&
        s->st_ctim.tv_sec==(int64_t)expected[8]&&s->st_ctim.tv_nsec==(int64_t)expected[9];
}
int vector_layout_identity(int fd,uint64_t *device,uint64_t *inode,uint64_t *bytes) {
    for(unsigned i=0;i<7;++i)if(fd>=0&&fd==descriptors[i]) {
        struct stat fresh;if(fstat(fd,&fresh)||!identity(&fresh,&identities[i]))return 0;
        *device=fresh.st_dev;*inode=fresh.st_ino;*bytes=fresh.st_size;return 1;
    }
    return 0;
}
uint64_t vector_layout_now(void) {
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
int vector_layout_record(const char *text){return report("%s",text);}
static void retain(void) {
    (void)report("RETAIN sources_and_Direct_backing=1 no_retry=1 GPU_calls=0");for(;;)usleep(1000000);
}
static int headroom(unsigned extra) {
    uint32_t a=0,b=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&a,&minimum,&reserved,&page,&b};
    for(unsigned i=0;i<5;++i){size_t n=4;if(sysctlbyname(names[i],values[i],&n,NULL,0)||n!=4)return 0;}
    const uint64_t required=(uint64_t)minimum+(reserved>256?reserved:256)+extra;
    const int rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    if(extra&&!report("PREALLOC_HEADROOM free_first=%u free_last=%u required=%llu flexible_bytes=%zu rc=%d",a,b,(unsigned long long)required,flexible,rc))return 0;
    return page==PAGE&&minimum&&reserved&&reserved<=minimum&&required<=UINT32_MAX&&a>=required&&b>=required&&!rc&&flexible>=(264u<<20);
}
int vector_layout_permit(void){return headroom(0);}
static int digest(const void *data,size_t bytes,const unsigned char expected[32]) {
    sha256_t hash;unsigned char actual[32];sha256_init(&hash);sha256_update(&hash,data,bytes);sha256_final(&hash,actual);return !memcmp(actual,expected,32);
}
static int verify_read(int fd,void *target,size_t bytes,uint64_t offset) {
    if(!headroom(0)||!report("VERIFY_BEFORE offset=%llu bytes=%zu",(unsigned long long)offset,bytes))return 0;
    pending=1;const ssize_t got=pread(fd,target,bytes,offset);pending=0;
    if(!report("VERIFY_RETURNED result=%lld",(long long)got))retain();return got==(ssize_t)bytes;
}
static int close_source(unsigned i) {
    struct stat fresh;if(descriptors[i]<0)return 1;
    const int valid=!fstat(descriptors[i],&fresh)&&identity(&fresh,&identities[i]);
    if(close(descriptors[i]))retain();descriptors[i]=-1;return valid;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,mapped=0,rc=0;int64_t physical=-1;unsigned char *window=NULL;
    output_fd=open(LAYOUT_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s Direct_bytes=%u samples=18 groups=3 modes=2 rounds=8 original_BF16=1 copies=0 GPU_calls=0 title_launches=0",CLOSE_NONCE,WINDOW))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
        !headroom(WINDOW/PAGE)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("DIRECT_ALLOC_BEFORE"))goto done;
    rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,PAGE,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();if(rc<0){if(physical>=0)retain();goto done;}if(physical<0)retain();
    if(!report("DIRECT_MAP_BEFORE"))retain();rc=sceKernelMapDirectMemory((void **)&window,WINDOW,3,0,physical,PAGE);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc)||rc<0||!window||(uintptr_t)window%PAGE)retain();mapped=1;
    if(seteuid(1)||geteuid()!=1)goto finish;
    descriptors[6]=open(LAYOUT_PACK,O_RDONLY|O_DIRECT|O_NOFOLLOW);
    if(descriptors[6]<0||fstat(descriptors[6],&identities[6])||!S_ISREG(identities[6].st_mode)||!identities[6].st_ino||
        identities[6].st_size!=(off_t)LAYOUT_PACK_BYTES||(fcntl(descriptors[6],F_GETFL)&O_DIRECT)!=O_DIRECT)goto finish;
    sha256_t hash;sha256_init(&hash);
    for(uint64_t offset=0;offset<LAYOUT_PACK_BYTES;) {
        size_t n=LAYOUT_PACK_BYTES-offset;if(n>SCRATCH)n=SCRATCH;
        if(n%PAGE||!verify_read(descriptors[6],window,n,offset))goto finish;sha256_update(&hash,window,n);offset+=n;
    }
    unsigned char actual[32];sha256_final(&hash,actual);if(memcmp(actual,layout_pack_SHA256,32))goto finish;
    if(!report("EOF_BEFORE pack=1"))goto finish;pending=1;const ssize_t tail=pread(descriptors[6],window,PAGE,LAYOUT_PACK_BYTES);pending=0;
    if(!report("EOF_RETURNED pack=1 bytes=%lld",(long long)tail))retain();if(tail)goto finish;
    if(!report("PACK_complete_SHA256_identity_EOF=1"))goto finish;
    /* Verify every selected original envelope before any timing. Whole original
     * lineage is reused only with exact sealed identities; unused bytes are not read. */
    for(unsigned g=0;g<3;++g)for(unsigned i=0;i<6;++i) {
        descriptors[i]=open(layout_sources[g][i].path,O_RDONLY|O_DIRECT|O_NOFOLLOW);
        if(descriptors[i]<0||fstat(descriptors[i],&identities[i])||!sealed(&identities[i],layout_sources[g][i].identity)||
            (fcntl(descriptors[i],F_GETFL)&O_DIRECT)!=O_DIRECT||!verify_read(descriptors[i],window,STRIDE,layout_sources[g][i].offset)||
            !digest(window,STRIDE,layout_sources[g][i].envelope_SHA256)||!digest(window+layout_residue[g][i],MATRIX,layout_raw_SHA256[g][i]))goto finish;
        if(!report("EOF_BEFORE group=%u item=%u",g,i))retain();pending=1;
        const uint64_t end=(identities[i].st_size+PAGE-1)/PAGE*PAGE;const ssize_t got=pread(descriptors[i],window,PAGE,end);pending=0;
        if(!report("EOF_RETURNED group=%u item=%u bytes=%lld",g,i,(long long)got))retain();if(got||!close_source(i))goto finish;
    }
    if(!report("ORIGINAL_selected_18_envelopes_SHA256_sealed_identity_EOF=1"))goto finish;
    if(!headroom(0)||!vector_layout_start())retain();worker_started=1;
    const uint64_t start=vector_layout_now();if(!start)goto finish;
    unsigned char *destination=window+SCRATCH;
    for(unsigned round=0;round<8;++round)for(unsigned shifted=0;shifted<3;++shifted) {
        const unsigned g=(round+shifted)%3;struct vector_layout_source control[6],candidate[6];
        for(unsigned i=0;i<6;++i) {
            descriptors[i]=open(layout_sources[g][i].path,O_RDONLY|O_DIRECT|O_NOFOLLOW);
            if(descriptors[i]<0||fstat(descriptors[i],&identities[i])||!sealed(&identities[i],layout_sources[g][i].identity)||
                (fcntl(descriptors[i],F_GETFL)&O_DIRECT)!=O_DIRECT)goto finish;
            control[i]=(struct vector_layout_source){descriptors[i],layout_sources[g][i].offset};
            candidate[i]=(struct vector_layout_source){descriptors[6],layout_pack_offsets[g][i]};
        }
        for(unsigned order=0;order<2;++order) {
            const unsigned mode=(round+order)%2;
            if(vector_layout_now()-start>UINT64_C(40000000000)||!headroom(0))goto finish;
            memset(destination,0xa7,WINDOW-SCRATCH);
            if(!report("BATCH_BEGIN round=%u group=%u mode=%u",round,g,mode))retain();
            struct vector_layout_times times;const int result=vector_layout_batch(mode,mode?candidate:control,destination,&times);
            if(result<0)retain();if(!result)goto finish;
            if(!report("BATCH_DRAINED round=%u group=%u mode=%u wall_ns=%llu source_ns=%llu physical_bytes=%llu copies=0",
                round,g,mode,(unsigned long long)times.wall_ns,(unsigned long long)times.source_ns,(unsigned long long)times.physical_bytes))retain();
            for(unsigned i=0;i<6;++i)if(!digest(destination+i*STRIDE+layout_residue[g][i],MATRIX,layout_raw_SHA256[g][i])||
                !digest(destination+i*STRIDE,STRIDE,mode?layout_pack_envelope_SHA256[g][i]:layout_sources[g][i].envelope_SHA256))goto finish;
            for(unsigned i=6*STRIDE;i<WINDOW-SCRATCH;++i)if(destination[i]!=0xa7)goto finish;
            if(!report("BATCH_EXACT round=%u group=%u mode=%u original_SHA256=6 envelope_SHA256=6 tail_canary=1",round,g,mode))goto finish;
        }
        for(unsigned i=0;i<6;++i)if(!close_source(i))goto finish;
    }
    ok=1;
finish:
    if(pending)retain();if(worker_started){if(!vector_layout_stop())retain();worker_stopped=1;}
    for(unsigned i=0;i<7;++i)if(!close_source(i))ok=0;
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom(0)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(worker_started&&!worker_stopped)retain();
    if(mapped){if(!report("DIRECT_UNMAP_BEFORE"))retain();rc=sceKernelMunmap(window,WINDOW);if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        if(!report("DIRECT_RELEASE_BEFORE"))retain();rc=sceKernelReleaseDirectMemory(physical,WINDOW);if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;}
    if(!report("END success=%d nonce=%s all_workers_joined=%d Direct_released=%d pending_reads=0 GPU_calls=0 title_launches=0 no_retry=1",ok,CLOSE_NONCE,worker_stopped,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
