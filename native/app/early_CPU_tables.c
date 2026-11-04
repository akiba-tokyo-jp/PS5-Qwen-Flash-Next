/* SPDX-License-Identifier: MIT
 * Back only the audited application-owned zero-table hole before C++ setup.
 * No source file, model, Vulkan, display, kernel patch or worker is started.
 */
#include "early_CPU_tables.h"
#include "early_CPU_tables_manifest.h"
#include "sha256.h"
#include <ps5platform/kernel.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/sysctl.h>
extern void qwen_native_stage(const char*);
extern void qwen_native_halt(const char*) __attribute__((noreturn));
extern unsigned char __qwen_driver_tables_start[],__qwen_driver_tables_end[],__qwen_early_tables_end[];
struct original_table {unsigned char*target;uint64_t bytes,offset,stored;unsigned char digest[32];};
struct original_plan {const struct original_table*tables;uint64_t count;const unsigned char*packed;uint64_t packed_bytes;unsigned char*begin,*end;};
extern const struct original_plan qwen_driver_table_storage;
_Static_assert(sizeof(struct original_plan)==48&&sizeof(struct original_table)==64,"Original native table ABI required");
static struct qwen_early_CPU_tables result={.physical=-1};
const struct qwen_early_CPU_tables*qwen_early_CPU_tables_result(void){return &result;}
static int sample(void){
    uint32_t free=0,minimum=0;size_t a=4,b=4;
    if(sysctlbyname("vm.stats.vm0.v_free_count",&free,&a,0,0)||a!=4||
       sysctlbyname("vm.stats.vm0.v_free_min",&minimum,&b,0,0)||b!=4||minimum!=898)return 0;
    if(!result.free_before)result.free_before=free;result.free_after=free;
    if(!result.minimum_free||free<result.minimum_free)result.minimum_free=free;
    return free>=minimum+21;
}
static void returned(void){
    char line[384];result.all_CPU_operations_returned=1;
    snprintf(line,sizeof(line),"early_CPU_tables_returned status=%d mapped=%d zeroed=%d checksum=%d mapping_bytes=%llu allocation_bytes=%llu minimum_free=%u CPU_IO_returned=1 model_GPU_calls=0",
        result.status,result.mapped,result.zeroed,result.checksum_passed,(unsigned long long)result.mapped_bytes,
        (unsigned long long)result.allocated_bytes,result.minimum_free);
    qwen_native_stage(line);
    if(result.status)qwen_native_halt("early_CPU_tables_returned_failure_before_original_CXX_GPU_not_started");
}
__attribute__((constructor(101))) static void early_CPU_tables_map(void){
    qwen_native_stage("early_CPU_tables_begin_before_original_CXX_GPU_not_started");result.status=1;
    const uintptr_t begin=(uintptr_t)__qwen_driver_tables_start,end=(uintptr_t)__qwen_driver_tables_end,
        owned_end=(uintptr_t)__qwen_early_tables_end;
    const struct original_plan*plan=&qwen_driver_table_storage;
    result.begin=begin;result.end=owned_end;
    if(!begin||begin%65536||end-begin!=EARLY_ORIGINAL_TABLE_BYTES||owned_end-begin!=EARLY_DIRECT_BYTES||
       owned_end%65536||!plan->tables||!plan->packed||plan->count!=673||plan->begin!=(void*)begin||
       plan->end!=(void*)end||plan->packed_bytes!=EARLY_PACKED_BYTES||!sample())goto done;
    uint64_t sum=0;
    for(unsigned i=0;i<673;++i){
        const struct original_table*table=plan->tables+i;const uintptr_t at=(uintptr_t)table->target;
        if(at<begin||at>=end||!table->bytes||table->bytes>end-at)goto done;
        for(unsigned j=0;j<i;++j){const uintptr_t other=(uintptr_t)plan->tables[j].target;
            if(at<other+plan->tables[j].bytes&&other<at+table->bytes)goto done;}
        sum+=table->bytes;
    }
    if(sum!=9471408)goto done;
    result.status=2;void*region_begin=0,*region_end=0;uint32_t protection=0;
    if(!sceKernelQueryMemoryProtection((void*)begin,&region_begin,&region_end,&protection))goto done;
    void*reserved=(void*)begin;
    if(sceKernelReserveVirtualRange(&reserved,EARLY_DIRECT_BYTES,0,65536))goto done;
    if(reserved!=(void*)begin){(void)sceKernelMunmap(reserved,EARLY_DIRECT_BYTES);goto done;}
    result.status=3;const int64_t pool=sceKernelGetDirectMemorySize();int64_t start=-1;size_t available=0;
    if(pool<=0||sceKernelAvailableDirectMemorySize(0,pool,65536,&start,&available)||start<0||
       available<EARLY_DIRECT_BYTES+(256ull<<20)||!sample())goto done;
    result.available_before=available;
    if(sceKernelAllocateDirectMemory(0,pool,EARLY_DIRECT_BYTES,65536,PS5_KERNEL_DIRECT_TYPE_CPU,&result.physical)||result.physical<0)goto done;
    result.allocated=1;result.allocated_bytes=EARLY_DIRECT_BYTES;result.status=4;
    void*actual=(void*)begin;
    if(sceKernelMapDirectMemory(&actual,EARLY_DIRECT_BYTES,3,PS5_KERNEL_MAP_FIXED,result.physical,16384)||actual!=(void*)begin)goto done;
    result.mapped=1;result.mapped_bytes=EARLY_DIRECT_BYTES;result.status=5;
    if(sceKernelQueryMemoryProtection((void*)begin,&region_begin,&region_end,&protection)||
       (uintptr_t)region_begin>begin||(uintptr_t)region_end<owned_end||(protection&7)!=3||!sample())goto done;
    memset((void*)begin,0,EARLY_DIRECT_BYTES);result.zeroed=1;
    struct ai_sha256 hash;ai_sha256_init(&hash);unsigned char digest[32];
    for(size_t at=0;at<EARLY_DIRECT_BYTES;at+=65536){if(!sample())goto done;ai_sha256_update(&hash,(void*)(begin+at),65536);}
    ai_sha256_final(&hash,digest);if(memcmp(digest,early_zero_SHA256,32))goto done;
    result.status=0;
done:returned();
}
__attribute__((constructor(102))) static void early_CPU_tables_check(void){
    if(result.status)return;
    uint64_t value=UINT64_C(14695981039346656037);const volatile unsigned char*bytes=(void*)(uintptr_t)result.begin;
    for(size_t i=0;i<EARLY_DIRECT_BYTES;++i){value^=bytes[i];value*=UINT64_C(1099511628211);}
    result.checksum=value;result.checksum_passed=value==EARLY_ZERO_FNV64;
    if(!result.checksum_passed)result.status=6;returned();
}
