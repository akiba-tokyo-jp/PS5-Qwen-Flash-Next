/* SPDX-License-Identifier: GPL-3.0-or-later
 * Replace one owned anonymous CPU page, preserving both adjacent guards.
 */
#include "qualified_context_guard.c"
#include "direct_vm_calibration_context.h"
#include <ps5platform/kernel.h>
#include <sys/mman.h>
#include <fcntl.h>
enum { PAGE_BYTES=16384, FLEX_BYTES=4*PAGE_BYTES, DIRECT_BYTES=65536 };
static int floor_ok(void) {
    uint32_t free=0,minimum=0,reserved=0;size_t bytes=4;
    if(sysctlbyname("vm.stats.vm0.v_free_count",&free,&bytes,NULL,0)||bytes!=4)return 0;
    bytes=4;if(sysctlbyname("vm.stats.vm0.v_free_min",&minimum,&bytes,NULL,0)||bytes!=4)return 0;
    bytes=4;if(sysctlbyname("vm.stats.vm0.v_free_reserved",&reserved,&bytes,NULL,0)||bytes!=4)return 0;
    const uint64_t required=(uint64_t)minimum+(reserved>256?reserved:256)+23;
    return report("CPU_FIXED_HEADROOM free=%u required=%llu",free,(unsigned long long)required)&&free>=required;
}
int main(int argc,char **argv) {
    (void)argv;int ok=0,allocated=0,mapped=0;int64_t physical=-1;unsigned char *flex=MAP_FAILED,*target=NULL;
    output_fd=open(DIRECT_VM_LOG,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);output_selected=1;if(output_fd<0)return 2;
    if(!report("BEGIN nonce=%s CPU_only=1 GPU_calls=0 title_launches=0 maximum_Direct_bytes=%u maximum_Flexible_bytes=%u",CLOSE_NONCE,DIRECT_BYTES,FLEX_BYTES))goto done;
    if((argc!=0&&argc!=1)||constructors!=1||getuid()!=1||geteuid()!=0||!context(1)||!context(2)||
       sceSystemServiceGetAppIdOfRunningBigApp()!=-1||!floor_ok())goto done;
    flex=mmap(NULL,FLEX_BYTES,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);
    if(!report("CPU_FLEX_MAP_RETURNED success=%d",flex!=MAP_FAILED)||flex==MAP_FAILED||(uintptr_t)flex%PAGE_BYTES)goto done;
    for(unsigned p=0;p<4;++p)memset(flex+p*PAGE_BYTES,0x40+p,PAGE_BYTES);
    unsigned index=1;if(((uintptr_t)flex+PAGE_BYTES)%65536==0)index=2;target=flex+index*PAGE_BYTES;
    if(!floor_ok())goto done;
    const int64_t pool=sceKernelGetDirectMemorySize();int64_t available_start=-1;size_t available=0;
    if(pool<0||(pool>0&&(sceKernelAvailableDirectMemorySize(0,pool,65536,&available_start,&available)||available<DIRECT_BYTES)))goto done;
    int rc=sceKernelAllocateDirectMemory(0,pool,DIRECT_BYTES,65536,PS5_KERNEL_DIRECT_TYPE_CPU,&physical);
    if(!report("CPU_DIRECT_ALLOC_RETURNED rc=%d owned=%d",rc,!rc&&physical>=0)||rc||physical<0)goto done;allocated=1;
    void *actual=target;
    if(!report("CPU_FIXED_MAP_BEFORE owned_page_index=%u target_mod_64KiB=%zu bytes=%u alignment=%u",index,(size_t)((uintptr_t)target%65536),PAGE_BYTES,PAGE_BYTES))goto done;
    rc=sceKernelMapDirectMemory(&actual,PAGE_BYTES,3,PS5_KERNEL_MAP_FIXED,physical,PAGE_BYTES);
    if(!report("CPU_FIXED_MAP_RETURNED rc=%d exact_address=%d",rc,actual==target)||rc)goto done;
    mapped=1;if(actual!=target)goto done;
    for(unsigned p=0;p<4;++p)if(p!=index)for(unsigned i=0;i<PAGE_BYTES;++i)if(flex[p*PAGE_BYTES+i]!=0x40+p)goto done;
    memset(target,0x9b,PAGE_BYTES);
    if(mprotect(target,PAGE_BYTES,PROT_READ))goto done;
    void *begin=NULL,*end=NULL;uint32_t protection=0;
    rc=sceKernelQueryMemoryProtection(target,&begin,&end,&protection);
    if(!report("CPU_FIXED_PROTECTION rc=%d contains=%d CPU_read=%d CPU_write=%d",rc,
        (uintptr_t)begin<=(uintptr_t)target&&(uintptr_t)end>=(uintptr_t)target+PAGE_BYTES,!!(protection&1),!!(protection&2))||
       rc||(uintptr_t)begin>(uintptr_t)target||(uintptr_t)end<(uintptr_t)target+PAGE_BYTES||!(protection&1)||(protection&2))goto done;
    for(unsigned i=0;i<PAGE_BYTES;++i)if(target[i]!=0x9b)goto done;
    if(!context(3)||sceSystemServiceGetAppIdOfRunningBigApp()!=-1)goto done;ok=1;
done:
    if(mapped){const int rc=sceKernelMunmap(target,PAGE_BYTES);if(!report("CPU_FIXED_UNMAP_RETURNED rc=%d",rc)||rc)ok=0;else mapped=0;}
    if(flex!=MAP_FAILED){const int rc=munmap(flex,FLEX_BYTES);if(!report("CPU_FLEX_UNMAP_RETURNED rc=%d",rc)||rc)ok=0;}
    if(allocated&&!mapped){const int rc=sceKernelReleaseDirectMemory(physical,DIRECT_BYTES);if(!report("CPU_DIRECT_RELEASE_RETURNED rc=%d",rc)||rc)ok=0;else allocated=0;}
    if(!report("END success=%d nonce=%s live_Direct_bytes=%u all_neighbor_patterns_exact=%d readonly_exact=%d GPU_calls=0 title_launches=0 automatic_retry=0",ok,CLOSE_NONCE,allocated?DIRECT_BYTES:0,ok,ok))ok=0;
    if(close(output_fd))ok=0;return ok?0:1;
}
