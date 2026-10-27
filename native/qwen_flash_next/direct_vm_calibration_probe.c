/* SPDX-License-Identifier: GPL-3.0-or-later
 * Measure Direct allocation/mapping VM cost separately from payload capacity.
 */
#include "qualified_context_guard.c"
#include "direct_vm_calibration_context.h"
#include "kernel_memory_trace.h"
#include <ps5platform/kernel.h>
#include <fcntl.h>
#include <time.h>

#ifndef DIRECT_VM_ALIGNMENT
#define DIRECT_VM_ALIGNMENT 65536
#endif
enum { PAGE_BYTES=16384, ALIGN_BYTES=DIRECT_VM_ALIGNMENT, PHASES=8 };
#ifdef DIRECT_VM_ONLY_BYTES
enum { CASES=3 };
_Static_assert(DIRECT_VM_ONLY_BYTES==29360128&&DIRECT_VM_ALIGNMENT==16384,"Exact remaining helper capacity");
static const size_t sizes[4]={DIRECT_VM_ONLY_BYTES,DIRECT_VM_ONLY_BYTES,DIRECT_VM_ONLY_BYTES,DIRECT_VM_ONLY_BYTES};
#else
enum { CASES=12 };
#if DIRECT_VM_ALIGNMENT == 16384
static const size_t sizes[4]={98304,8388608,20971520,25165824};
#else
_Static_assert(DIRECT_VM_ALIGNMENT==65536,"Exact qualified calibration alignment");
static const size_t sizes[4]={65536,1048576,8388608,20971520};
#endif
#endif
static struct qwen_kernel_memory_sample samples[CASES][PHASES],idles[CASES][2];
static uint64_t elapsed[CASES][PHASES];
static unsigned complete,allocated_count,mapped_count,unmapped_count,released_count;
static int64_t physical=-1;
static unsigned char *address;
static size_t owned_bytes;
static int mapped;
static uint64_t begun;

static uint64_t now(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)return 0;
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}
static int scalar(void *unused,const char *name,uint32_t *value) {
    (void)unused;struct {uint64_t a;uint32_t value;uint64_t b;} g={GUARD,0,GUARD};
    size_t bytes=sizeof(g.value);
    if(sysctlbyname(name,&g.value,&bytes,NULL,0)||bytes!=sizeof(g.value)||g.a!=GUARD||g.b!=GUARD)return 0;
    *value=g.value;return 1;
}
static int observe(struct qwen_kernel_memory_sample *s,unsigned phase) {
    const uint64_t current=now();
    return current&&current>=begun&&current-begun<=UINT64_C(20000000000)&&
        qwen_kernel_memory_observe(NULL,scalar,current,phase,s);
}
static int permit(const struct qwen_kernel_memory_sample *s) {
    return qwen_kernel_memory_floor(s,0);
}
static void retain(void) {
    (void)report("RETAIN owned_Direct_backing=1 completion_not_established=1 automatic_retry=0 GPU_calls=0");
    for(;;)usleep(1000000);
}
static int retire(void) {
    if(mapped) {
        const int rc=sceKernelMunmap(address,owned_bytes);
        if(rc||!report("UNMAP_RETURNED case=%u rc=%d",complete,rc))retain();
        mapped=0;address=NULL;++unmapped_count;
    }
    if(physical>=0) {
        const int rc=sceKernelReleaseDirectMemory(physical,owned_bytes);
        if(rc||!report("RELEASE_RETURNED case=%u rc=%d",complete,rc))retain();
        physical=-1;owned_bytes=0;++released_count;
    }
    return 1;
}
static uint64_t pattern(unsigned iteration,size_t page) {
    return GUARD^((uint64_t)iteration<<40)^((uint64_t)page<<8);
}
static int exercise(unsigned i) {
    /* Balanced size order; idle and resource phases use the same observer. */
    const unsigned slot=(i%4+i/4)%4;const size_t bytes=sizes[slot];
    const struct timespec delay={0,20000000};
    if(!observe(&idles[i][0],0)||!permit(&idles[i][0])||nanosleep(&delay,NULL)||
       !observe(&idles[i][1],0)||!permit(&idles[i][1])||
       !observe(&samples[i][0],1)||!permit(&samples[i][0]))return 0;
    const int64_t pool=sceKernelGetDirectMemorySize();
    int64_t available_start=-1;size_t available=0,flexible=0;
    const int query=pool>0?sceKernelAvailableDirectMemorySize(0,pool,ALIGN_BYTES,&available_start,&available):-1;
    const int flexible_rc=sceKernelAvailableFlexibleMemorySize(&flexible);
    if(!report("DIRECT_BUDGET case=%u bytes=%zu pool=%lld query_rc=%d available=%zu flexible_rc=%d flexible_bytes=%zu context_zero_is_not_capacity=1",
       i,bytes,(long long)pool,query,available,flexible_rc,flexible))return 0;
    if(pool<0||(pool>0&&(query||available_start<0||available<bytes))||flexible_rc||flexible<(1u<<20))return 0;
    /* The existing CPU control qualified this exact allocation API forwarding
     * a zero context value. The returned status, not that value, grants ownership.
     */
    owned_bytes=bytes;
    uint64_t start=now();
    if(!report("ALLOC_BEFORE case=%u bytes=%zu",i,bytes))return 0;
    int rc=sceKernelAllocateDirectMemory(0,pool,bytes,ALIGN_BYTES,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    elapsed[i][0]=now()-start;
    if(!report("ALLOC_RETURNED case=%u rc=%d",i,rc))retain();
    if(rc){if(physical>=0)retain();owned_bytes=0;return 0;}if(physical<0)retain();++allocated_count;
    if(!observe(&samples[i][1],2)||!permit(&samples[i][1]))return 0;
    start=now();
    if(!report("MAP_BEFORE case=%u",i))return 0;
    rc=sceKernelMapDirectMemory((void **)&address,bytes,3,0,physical,ALIGN_BYTES);
    elapsed[i][1]=now()-start;
    if(!report("MAP_RETURNED case=%u rc=%d",i,rc)||rc||!address||(uintptr_t)address%ALIGN_BYTES)retain();
    mapped=1;++mapped_count;
    if(!observe(&samples[i][2],3)||!permit(&samples[i][2]))return 0;
    start=now();
    for(size_t p=0;p<bytes/PAGE_BYTES;++p) {
        volatile uint64_t *first=(volatile uint64_t *)(address+p*PAGE_BYTES);
        volatile uint64_t *last=(volatile uint64_t *)(address+(p+1)*PAGE_BYTES-sizeof(uint64_t));
        *first=pattern(i,p);*last=~pattern(i,p);
    }
    elapsed[i][2]=now()-start;
    if(!observe(&samples[i][3],4)||!permit(&samples[i][3]))return 0;
    start=now();
    for(size_t p=0;p<bytes/PAGE_BYTES;++p) {
        volatile uint64_t *first=(volatile uint64_t *)(address+p*PAGE_BYTES);
        volatile uint64_t *last=(volatile uint64_t *)(address+(p+1)*PAGE_BYTES-sizeof(uint64_t));
        if(*first!=pattern(i,p)||*last!=~pattern(i,p))return 0;
    }
    elapsed[i][3]=now()-start;
    if(!observe(&samples[i][4],5)||!permit(&samples[i][4]))return 0;
    start=now();rc=sceKernelMunmap(address,bytes);elapsed[i][4]=now()-start;
    if(rc||!report("UNMAP_RETURNED case=%u rc=%d",i,rc))retain();
    mapped=0;address=NULL;++unmapped_count;
    if(!observe(&samples[i][5],6))return 0;
    start=now();rc=sceKernelReleaseDirectMemory(physical,bytes);elapsed[i][5]=now()-start;
    if(rc||!report("RELEASE_RETURNED case=%u rc=%d",i,rc))retain();
    physical=-1;owned_bytes=0;++released_count;
    if(!observe(&samples[i][6],7)||!permit(&samples[i][6])||nanosleep(&delay,NULL)||
       !observe(&samples[i][7],8)||!permit(&samples[i][7]))return 0;
    if(!report("CASE_COMPLETE case=%u bytes=%zu all_page_patterns_exact=1",i,bytes))return 0;
    ++complete;return 1;
}
static int emit(const char *kind,unsigned i,unsigned phase,const struct qwen_kernel_memory_sample *s) {
    return report("SAMPLE kind=%s case=%u phase=%u ns=%llu free_first=%u free_last=%u active=%u inactive=%u wired=%u cache=%u total=%u minimum=%u reserved=%u target=%u page_bytes=%u",
        kind,i,phase,(unsigned long long)s->monotonic_ns,s->free_first,s->free_last,s->active,s->inactive,s->wired,s->cache,
        s->total,s->minimum,s->reserved,s->target,s->page_bytes);
}
int main(int argc,char **argv) {
    (void)argv;int ok=0;
    output_fd=open(DIRECT_VM_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;
    if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s CPU_only=1 title_launches=0 GPU_calls=0 cases=%u maximum_Direct_bytes=%u alignment_bytes=%u VM_payload_charge_pages=0",CLOSE_NONCE,CASES,(unsigned)sizes[3],ALIGN_BYTES))return 2;
    begun=now();
    if((argc!=0&&argc!=1)||!begun||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    for(unsigned i=0;i<CASES;++i)if(!exercise(i))goto done;
    if(!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;
    ok=1;
done:
    retire();
    for(unsigned i=0;i<CASES;++i) {
        for(unsigned p=0;p<2;++p)if(idles[i][p].monotonic_ns&&!emit("idle",i,p,&idles[i][p]))ok=0;
        for(unsigned p=0;p<PHASES;++p)if(samples[i][p].monotonic_ns&&!emit("resource",i,p,&samples[i][p]))ok=0;
        if(!report("TIMING case=%u allocate_ns=%llu map_ns=%llu touch_ns=%llu verify_ns=%llu unmap_ns=%llu release_ns=%llu",i,
            (unsigned long long)elapsed[i][0],(unsigned long long)elapsed[i][1],(unsigned long long)elapsed[i][2],
            (unsigned long long)elapsed[i][3],(unsigned long long)elapsed[i][4],(unsigned long long)elapsed[i][5]))ok=0;
    }
    if(!report("END success=%d nonce=%s completed=%u allocated=%u mapped=%u unmapped=%u released=%u live_Direct_bytes=%zu GPU_calls=0 title_launches=0 automatic_retry=0",
       ok,CLOSE_NONCE,complete,allocated_count,mapped_count,unmapped_count,released_count,owned_bytes))ok=0;
    if(fsync(output_fd)||close(output_fd))ok=0;return ok?0:1;
}
