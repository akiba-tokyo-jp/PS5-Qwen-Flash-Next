/* SPDX-License-Identifier: MIT
 * Read-only exact-byte comparison of two/four CPU reads. No GPU or model load.
 */
#include "qualified_context_guard.c"
#include "queued_source_context.h"
#include "queued_source_probe_io.h"
#include "hash/sha256/sha256.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <time.h>
#define WINDOW (8u<<20)
#define ALIGNMENT 16384u
#define SAMPLES 8u
_Static_assert(QUEUED_QUADS>=SAMPLES,"Sample the complete prepared trace range");
static int source_fds[8],source_ids[8];
static uint64_t ages[8],tick;
static int pool_started,pool_stopped;
static uint64_t now_ns(void){
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return(uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static int headroom(void){
    uint32_t free_first=0,free_last=0,minimum=0,reserved=0,page=0;size_t flexible=0;
    const char *names[]={"vm.stats.vm0.v_free_count","vm.stats.vm0.v_free_min","vm.stats.vm0.v_free_reserved","hw.pagesize","vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&free_first,&minimum,&reserved,&page,&free_last};
    for(unsigned i=0;i<5;++i){size_t bytes=4;if(sysctlbyname(names[i],values[i],&bytes,NULL,0)||bytes!=4)return 0;}
    const uint32_t extra=reserved>256?reserved:256;
    return page==16384&&minimum&&reserved&&reserved<=minimum&&minimum<=UINT32_MAX-extra&&
        free_first>=minimum+extra&&free_last>=minimum+extra&&
        !sceKernelAvailableFlexibleMemorySize(&flexible)&&flexible>=(264u<<20);
}
static int identity(int fd,unsigned index){
    struct stat s;if(index>=QUEUED_FILES||fstat(fd,&s)||!S_ISREG(s.st_mode))return 0;
    uint64_t actual[]={s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_size,
        s.st_mtim.tv_sec,s.st_mtim.tv_nsec,s.st_ctim.tv_sec,s.st_ctim.tv_nsec};
    return !memcmp(actual,queued_files[index].identity,sizeof(actual));
}
static void retain(void){
    (void)report("RETAIN source_backing=1 pending_reads=%u no_retry=1 GPU_calls=0",queued_probe_pending());
    for(;;)usleep(1000000);
}
static int handle(unsigned index,const unsigned needed[4]){
    for(unsigned i=0;i<8;++i)if(source_fds[i]>=0&&source_ids[i]==(int)index){
        if(!identity(source_fds[i],index))return -1;ages[i]=++tick;return source_fds[i];}
    int slot=-1;
    for(unsigned i=0;i<8;++i){
        if(source_fds[i]<0){slot=(int)i;break;}
        int pinned=0;for(unsigned j=0;j<4;++j)if(source_ids[i]==(int)needed[j])pinned=1;
        if(!pinned&&(slot<0||ages[i]<ages[slot]))slot=(int)i;
    }
    if(slot<0||queued_probe_pending())return -1;
    if(source_fds[slot]>=0){if(!identity(source_fds[slot],(unsigned)source_ids[slot])||close(source_fds[slot]))return -1;source_fds[slot]=-1;}
    const int fd=open(queued_files[index].path,O_RDONLY|O_DIRECT|O_NOFOLLOW);
    if(fd<0)return -1;
    source_fds[slot]=fd;source_ids[slot]=(int)index;ages[slot]=++tick;
    return identity(fd,index)?fd:-1;
}
static int execute(const struct queued_probe_request requests[4],unsigned count,const uint64_t expected[4],uint64_t *elapsed){
    if(!headroom())return 0;
    if(!report("READ_BEFORE lanes=%u bytes=%zu",count,requests[0].bytes))return 0;
    const uint64_t begin=now_ns();if(!begin)return 0;
    int64_t got[4]={0};if(!queued_probe_read(requests,count,got))retain();
    const uint64_t end=now_ns();if(end<begin||queued_probe_pending())retain();
    if(!report("READ_RETURNED lanes=%u pending=0",count))retain();
    for(unsigned i=0;i<count;++i)if(got[i]<0||(uint64_t)got[i]!=expected[i])return 0;
    *elapsed+=end-begin;return 1;
}
int main(int argc,char **argv){
    (void)argv;int ok=0,mapped=0;int64_t physical=-1;void *window=NULL;
    for(unsigned i=0;i<8;++i){source_fds[i]=-1;source_ids[i]=-1;}
    output_fd=open(QUEUED_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s exact_trace=1 scratch_bytes=%u maximum_fds=8 source_quads=%u sample_quads=%u GPU_calls=0 title_launches=0",CLOSE_NONCE,WINDOW,QUEUED_QUADS,SAMPLES))return 2;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       !headroom()||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    if(!report("DIRECT_ALLOC_BEFORE bytes=%u",WINDOW))goto done;
    int rc=sceKernelAllocateDirectMemory(0,sceKernelGetDirectMemorySize(),WINDOW,ALIGNMENT,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("DIRECT_ALLOC_RETURNED rc=%d",rc))retain();
    if(rc<0){if(physical>=0)retain();goto done;}if(physical<0)retain();
    if(!report("DIRECT_MAP_BEFORE bytes=%u",WINDOW))retain();
    rc=sceKernelMapDirectMemory(&window,WINDOW,3,0,physical,ALIGNMENT);
    if(!report("DIRECT_MAP_RETURNED rc=%d",rc))retain();if(rc<0||!window||(uintptr_t)window%ALIGNMENT)retain();mapped=1;
    if(seteuid(1)||geteuid()!=1||!queued_probe_start())retain();pool_started=1;
    const uint64_t started=now_ns();if(!started)retain();
    for(unsigned round=0;round<6;++round)for(unsigned order=0;order<2;++order){
        const unsigned mode=(round+order)%2;
        for(unsigned q=0;q<SAMPLES;++q){
            if(now_ns()-started>UINT64_C(45000000000)||!headroom())goto finish;
            const struct queued_quad *quad=&queued_quads[q*(QUEUED_QUADS-1)/(SAMPLES-1)];int fds[4];unsigned needed[4];
            for(unsigned i=0;i<4;++i)needed[i]=quad->expert[i].file;
            for(unsigned i=0;i<4;++i){fds[i]=handle(needed[i],needed);if(fds[i]<0)goto finish;}
            sha256_t hashes[4];for(unsigned i=0;i<4;++i)sha256_init(&hashes[i]);
            uint64_t elapsed=0;unsigned calls=0;
            for(unsigned batch=0;batch<2;++batch){
                struct queued_probe_request requests[4]={{0}};uint64_t expected[4]={0};size_t skips[4]={0},logical[4]={0};
                const unsigned count=mode?4:2;
                for(unsigned i=0;i<count;++i){
                    const unsigned expert=mode?i:batch*2+i;
                    const struct queued_extent *extent=&quad->expert[expert];
                    const uint64_t done=mode&&batch?(2u<<20)-ALIGNMENT:0;
                    const size_t bytes=mode?(batch?(size_t)extent->bytes-((2u<<20)-ALIGNMENT):(2u<<20)-ALIGNMENT):(size_t)extent->bytes;
                    const uint64_t offset=extent->offset+done;skips[i]=(size_t)(offset%ALIGNMENT);logical[i]=bytes;
                    const size_t requested=(skips[i]+bytes+ALIGNMENT-1)/ALIGNMENT*ALIGNMENT;
                    requests[i]=(struct queued_probe_request){fds[expert],(unsigned char*)window+i*(WINDOW/count),requested,offset-skips[i]};
                    expected[i]=queued_files[extent->file].identity[5]-requests[i].offset;
                    if(expected[i]>requested)expected[i]=requested;
                    if(requested>WINDOW/count||expected[i]<skips[i]+logical[i])goto finish;
                }
                if(!execute(requests,count,expected,&elapsed))goto finish;calls+=count;
                for(unsigned i=0;i<count;++i){const unsigned expert=mode?i:batch*2+i;
                    sha256_update(&hashes[expert],(unsigned char*)requests[i].target+skips[i],logical[i]);}
            }
            for(unsigned i=0;i<4;++i){unsigned char hash[32];sha256_final(&hashes[i],hash);
                if(memcmp(hash,quad->expert[i].sha256,32))goto finish;}
            if(!report("QUAD round=%u mode=%u index=%u wall_ns=%llu logical_bytes=13107200 calls=%u exact_SHA256=1",round,mode,q,(unsigned long long)elapsed,calls))retain();
        }
    }
    ok=1;
finish:
    if(!queued_probe_stop()||queued_probe_pending())retain();pool_stopped=1;
    for(unsigned i=0;i<8;++i)if(source_fds[i]>=0){if(!identity(source_fds[i],(unsigned)source_ids[i])||close(source_fds[i])){ok=0;goto done;}source_fds[i]=-1;}
    if(seteuid(0)||geteuid()!=0||!context(3)||!headroom()||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)ok=0;
done:
    if(pool_started&&!pool_stopped)retain();
    for(unsigned i=0;i<8;++i)if(source_fds[i]>=0){if(close(source_fds[i]))ok=0;source_fds[i]=-1;}
    if(mapped){if(!report("DIRECT_UNMAP_BEFORE"))retain();rc=sceKernelMunmap(window,WINDOW);
        if(!report("DIRECT_UNMAP_RETURNED rc=%d",rc)||rc)retain();
        if(!report("DIRECT_RELEASE_BEFORE"))retain();rc=sceKernelReleaseDirectMemory(physical,WINDOW);
        if(!report("DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)retain();physical=-1;window=NULL;}
    if(!report("END success=%d nonce=%s pending_reads=%u all_workers_joined=%d Direct_released=%d GPU_calls=0 title_launches=0 automatic_retry=0",ok,CLOSE_NONCE,queued_probe_pending(),pool_stopped,physical<0))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
