/* SPDX-License-Identifier: MIT */
#include "file_residency.h"
#include <assert.h>
struct fake {unsigned admitted,marks,maps,queries,unmaps,fault;uint64_t offset;size_t size;};
static int admit(void *p){struct fake*f=p;++f->admitted;return f->fault!=1;}
static int mark(void*p,unsigned phase,unsigned edge){struct fake*f=p;++f->marks;return !(f->fault==2&&phase==2&&edge==1);}
static void *map(void*p,uint64_t offset,size_t size){struct fake*f=p;++f->maps;f->offset=offset;f->size=size;return f->fault==3?(void*)(intptr_t)-1:(void*)(uintptr_t)0x10000;}
static int query(void*p,const void*base,size_t size,char*vec){struct fake*f=p;++f->queries;assert(base==(void*)(uintptr_t)0x10000&&size==f->size);for(unsigned i=0;i<size/16384;++i)vec[i]=i%2?9:0;
    if(f->fault==4)return -1;
    if(f->fault==5)vec[0]=(char)0x80;
    if(f->fault==6)vec[64]=1;
    if(f->fault==8)vec[1]=1;
    return 0;}
static int unmap(void*p,void*base,size_t size){struct fake*f=p;++f->unmaps;assert(base==(void*)(uintptr_t)0x10000&&size==f->size);return f->fault==7?-1:0;}
int main(void){
    struct fake f={0};struct qwen_file_residency s={0};struct qwen_file_residency_ops o={&f,admit,mark,map,query,unmap};
    assert(qwen_file_residency_scan(&o,1048576+17,2,&s));assert(s.pages==65&&s.resident==32&&s.maps==2&&s.queries==2&&s.unmaps==2&&!s.live&&!s.pending);
    f=(struct fake){0};s=(struct qwen_file_residency){0};
    assert(qwen_file_residency_scan(&o,128u<<20,128,&s));assert(s.pages==8192&&s.resident==4096&&s.maps==128&&s.unmaps==128);
    for(unsigned fault=1;fault<=8;++fault){f=(struct fake){0};f.fault=fault;s=(struct qwen_file_residency){0};
        assert(!qwen_file_residency_scan(&o,17,1,&s));
        if(fault==7)assert(s.live&&f.unmaps==1);
        else assert(!s.live);
        if(fault>=4)assert(f.queries==1&&f.unmaps==1);
    }
    for(unsigned i=0;i<5;++i){f=(struct fake){0};s=(struct qwen_file_residency){0};
        uint64_t bytes=i==0?0:i==1?(128ull<<20)+1:2ull<<20;unsigned limit=i==2?0:i==3?129:1;
        assert(!qwen_file_residency_scan(&o,bytes,limit,&s));assert(!f.maps);
    }
    f=(struct fake){0};s=(struct qwen_file_residency){0};s.live=1;assert(!qwen_file_residency_scan(&o,17,1,&s));assert(!f.maps);
    return 0;
}
