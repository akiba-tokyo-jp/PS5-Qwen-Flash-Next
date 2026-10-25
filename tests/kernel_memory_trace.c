/* SPDX-License-Identifier: MIT */
#include "kernel_memory_trace.h"
#include <assert.h>
#include <string.h>
struct fake {unsigned call,fail,invalid;uint32_t before,after;};
static int read_counter(void *context,const char *name,uint32_t *value) {
    struct fake *f=context;const unsigned i=++f->call;
    if(i==f->fail)return 0;
    if(strstr(name,"free_count"))*value=i==1?f->before:f->after;
    else if(strstr(name,"pagesize"))*value=f->invalid==1?4096:16384;
    else if(strstr(name,"page_count"))*value=138739;
    else if(strstr(name,"free_min"))*value=898;
    else if(strstr(name,"free_reserved"))*value=206;
    else if(strstr(name,"free_target"))*value=f->invalid==2?800:2974;
    else if(strstr(name,"inactive_count"))*value=72000;
    else if(strstr(name,"active_count"))*value=28000;
    else if(strstr(name,"wire_count"))*value=f->invalid==3?150000:35000;
    else if(strstr(name,"cache_count"))*value=0;
    else return 0;
    return 1;
}
int main(void) {
    struct qwen_kernel_memory_sample s={0};
    struct fake f={0,0,0,2000,1999};
    assert(qwen_kernel_memory_observe(&f,read_counter,1,2,&s));
    assert(f.call==11&&s.phase==2&&s.free_first==2000&&s.free_last==1999&&s.inactive==72000);
    assert(qwen_kernel_memory_floor(&s,845));
    assert(!qwen_kernel_memory_floor(&s,846));
    s.free_last=1153;assert(!qwen_kernel_memory_floor(&s,0));
    s.free_last=1154;assert(qwen_kernel_memory_floor(&s,0));
    assert(!qwen_kernel_memory_floor(&s,UINT32_MAX));
    for(unsigned fail=1;fail<=11;++fail) {
        struct qwen_kernel_memory_sample previous=s;
        f=(struct fake){0,fail,0,2000,1999};
        assert(!qwen_kernel_memory_observe(&f,read_counter,1,0,&s));
        assert(!memcmp(&s,&previous,sizeof(s)));
    }
    for(unsigned invalid=1;invalid<=3;++invalid) {
        f=(struct fake){0,0,invalid,2000,1999};
        assert(!qwen_kernel_memory_observe(&f,read_counter,1,0,&s));
    }
    f=(struct fake){0,0,0,2000,1999};
    assert(!qwen_kernel_memory_observe(&f,read_counter,0,0,&s));
    assert(!qwen_kernel_memory_observe(&f,0,1,0,&s));
    assert(!qwen_kernel_memory_observe(&f,read_counter,1,0,0));
    return 0;
}
