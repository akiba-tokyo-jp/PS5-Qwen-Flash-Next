/* SPDX-License-Identifier: MIT */
#include "file_residency.h"
#include "file_residency_region.h"
#include <assert.h>
#include <stdio.h>
struct fixture {struct qwen_residency_region region;unsigned maps,queries,unmaps;uint64_t last;};
static int admit(void*c){(void)c;return 1;}
static int mark(void*c,unsigned p,unsigned e){(void)c;(void)p;(void)e;return 1;}
static void*map(void*c,uint64_t offset,size_t bytes){struct fixture*f=c;uint64_t actual=0;assert(qwen_residency_region_offset(&f->region,offset,bytes,&actual));assert(actual==f->region.offset+offset);f->last=actual;++f->maps;return(void*)(uintptr_t)0x400000;}
static int query(void*c,const void*p,size_t bytes,char*v){struct fixture*f=c;assert(p==(void*)(uintptr_t)0x400000);memset(v,1,bytes/16384);++f->queries;return 0;}
static int unmap(void*c,void*p,size_t bytes){struct fixture*f=c;(void)bytes;assert(p==(void*)(uintptr_t)0x400000);++f->unmaps;return 0;}
int main(void) {
    struct fixture f={{536870912,268451840,3293184,4},0,0,0,0};assert(qwen_residency_region_valid(&f.region));
    const struct qwen_file_residency_ops ops={&f,admit,mark,map,query,unmap};struct qwen_file_residency state={0};
    assert(qwen_file_residency_scan(&ops,f.region.bytes,f.region.maximum_windows,&state));
    assert(f.maps==4&&f.queries==4&&f.unmaps==4&&state.pages==201&&state.resident==201&&!state.live&&!state.pending);
    unsigned refusals=0;
    for(unsigned i=0;i<7;++i) {
        struct qwen_residency_region r=f.region;
        if(i==0)r.offset++;if(i==1)r.offset=r.file_bytes;if(i==2)r.bytes=0;if(i==3)r.bytes=(UINT64_C(128)<<20)+1;
        if(i==4)r.maximum_windows=3;if(i==5)r.maximum_windows=129;if(i==6)r.bytes=r.file_bytes-r.offset+1;
        assert(!qwen_residency_region_valid(&r));++refusals;
    }
    uint64_t actual=0;
    assert(!qwen_residency_region_offset(&f.region,1,16384,&actual));
    assert(!qwen_residency_region_offset(&f.region,0,16385,&actual));
    assert(!qwen_residency_region_offset(&f.region,4194304,16384,&actual));
    struct qwen_residency_region tail={32769,32768,1,1};assert(qwen_residency_region_offset(&tail,0,16384,&actual)&&actual==32768);
    printf("{\"invalid_region_refusals\":%u,\"invalid_window_refusals\":3,\"nonzero_offset_owned_mapping\":true,\"partial_EOF_page\":true,\"PS5_operations\":0}\n",refusals);
}
