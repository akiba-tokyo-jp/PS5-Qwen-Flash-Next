/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "launch_integrity.h"
static unsigned char storage[QWEN_LAUNCH_WINDOW+QWEN_LAUNCH_ALIGNMENT];
static unsigned char *window;
struct fixture {uint64_t clock,source_bytes,consumed,calls;int mode,before,after;};
static uint64_t now(void *p){struct fixture*f=p;return f->clock+=1000;}
static int memory(void *p){struct fixture*f=p;return f->mode!=1;}
static int marker(void *p,int before){struct fixture*f=p;if(before)++f->before;else++f->after;return f->mode!=(before?2:3);}
static int64_t read_at(void *p,void *data,size_t bytes,uint64_t offset){
    struct fixture*f=p;++f->calls;
    assert((uintptr_t)data%16384==0&&offset%16384==0&&bytes%16384==0&&bytes<=QWEN_LAUNCH_WINDOW);
    if(f->mode==4)return -1;
    if(f->mode==5)return (int64_t)bytes+1;
    if(f->mode==6)f->clock+=61000000000ull;
    if(f->mode==7&&f->calls==2)return 0;
    const size_t count=offset>=f->source_bytes?0:(f->source_bytes-offset>bytes?bytes:(size_t)(f->source_bytes-offset));
    for(size_t i=0;i<count;++i)((unsigned char*)data)[i]=(unsigned char)((offset+i)*17u+3u);
    return (int64_t)count;
}
static int consume(void *p,const unsigned char*data,size_t bytes){
    struct fixture*f=p;if(f->mode==8)return 0;
    for(size_t i=0;i<bytes;++i)assert(data[i]==(unsigned char)((f->consumed+i)*17u+3u));
    f->consumed+=bytes;return 1;
}
static struct qwen_launch_integrity state(struct fixture*f){
    struct qwen_launch_integrity s={0};s.context=f;s.now_ns=now;s.headroom=memory;s.marker=marker;s.read_at=read_at;s.consume=consume;return s;
}
int main(void){
    window=(unsigned char*)(((uintptr_t)storage+QWEN_LAUNCH_ALIGNMENT-1)&~(uintptr_t)(QWEN_LAUNCH_ALIGNMENT-1));
    const uint64_t sizes[]={1,16383,16384,16385,65535,65536,65537,27798695};
    for(unsigned i=0;i<sizeof(sizes)/sizeof(*sizes);++i){
        struct fixture f={.source_bytes=sizes[i]};struct qwen_launch_integrity s=state(&f);
        assert(qwen_launch_integrity_stream(&s,window,sizes[i],60));
        assert(f.consumed==sizes[i]&&f.before==f.after&&s.calls==s.returned&&!s.pending);
        assert(s.calls==(sizes[i]+QWEN_LAUNCH_WINDOW-1)/QWEN_LAUNCH_WINDOW+1);
        const uint64_t calls=f.calls;assert(!qwen_launch_integrity_stream(&s,window,sizes[i],60)&&f.calls==calls);
    }
    for(int mode=1;mode<=8;++mode){
        struct fixture f={.source_bytes=65537,.mode=mode};struct qwen_launch_integrity s=state(&f);
        assert(!qwen_launch_integrity_stream(&s,window,65537,60));assert(s.failed&&!s.pending&&s.calls==s.returned);
        const uint64_t calls=f.calls;assert(!qwen_launch_integrity_stream(&s,window,65537,60)&&f.calls==calls);
        if(mode<=2)assert(!f.calls);
    }
    for(int extra=-1;extra<=1;extra+=2){
        struct fixture f={.source_bytes=(uint64_t)(16384+extra)};struct qwen_launch_integrity s=state(&f);
        assert(!qwen_launch_integrity_stream(&s,window,16384,60)&&s.failed);
    }
    struct fixture f={.source_bytes=1};struct qwen_launch_integrity s=state(&f);
    assert(!qwen_launch_integrity_stream(&s,window+1,1,60)&&!f.calls);
    assert(!qwen_launch_integrity_stream(&s,window,0,60)&&!f.calls);
    assert(!qwen_launch_integrity_stream(&s,window,1,61)&&!f.calls);
    puts("Direct launch stream: aligned/tail/EOF/integrity, refusal, quarantine and no-replay controls passed");
}
