/* SPDX-License-Identifier: MIT */
#ifndef QWEN_KERNEL_MEMORY_TRACE_H
#define QWEN_KERNEL_MEMORY_TRACE_H
#include <stdint.h>
#include <stddef.h>

/* Metadata is diagnostic only. Inactive pages never grant admission. */
struct qwen_kernel_memory_sample {
    uint64_t monotonic_ns;
    uint32_t phase,free_first,free_last,total,minimum,reserved,target;
    uint32_t active,inactive,wired,cache,page_bytes;
};
typedef int (*qwen_kernel_counter)(void *,const char *,uint32_t *);
static int qwen_kernel_memory_observe(void *context,qwen_kernel_counter read,
                                    uint64_t now,uint32_t phase,
                                    struct qwen_kernel_memory_sample *out) {
    struct qwen_kernel_memory_sample s={0};
    if(!read||!out||!now)return 0;
    s.monotonic_ns=now;s.phase=phase;
    const char *names[]={"vm.stats.vm0.v_free_count","hw.pagesize",
        "vm.stats.vm0.v_page_count","vm.stats.vm0.v_free_min",
        "vm.stats.vm0.v_free_reserved","vm.stats.vm0.v_free_target",
        "vm.stats.vm0.v_active_count","vm.stats.vm0.v_inactive_count",
        "vm.stats.vm0.v_wire_count","vm.stats.vm0.v_cache_count",
        "vm.stats.vm0.v_free_count"};
    uint32_t *values[]={&s.free_first,&s.page_bytes,&s.total,&s.minimum,
        &s.reserved,&s.target,&s.active,&s.inactive,&s.wired,&s.cache,&s.free_last};
    for(size_t i=0;i<sizeof(names)/sizeof(names[0]);++i)
        if(!read(context,names[i],values[i]))return 0;
    if(s.page_bytes!=16384||!s.total||!s.reserved||s.reserved>s.minimum||
       s.minimum>=s.target||s.target>s.total||s.free_first>s.total||
       s.free_last>s.total||s.active>s.total||s.inactive>s.total||
       s.wired>s.total||s.cache>s.total)return 0;
    *out=s;return 1;
}
static int qwen_kernel_memory_floor(const struct qwen_kernel_memory_sample *s,
                                    uint32_t additional_pages) {
    if(!s)return 0;
    const uint64_t reserve=s->reserved>256?s->reserved:256;
    const uint64_t required=(uint64_t)s->minimum+reserve+additional_pages;
    return s->free_first>=required&&s->free_last>=required;
}
#endif
