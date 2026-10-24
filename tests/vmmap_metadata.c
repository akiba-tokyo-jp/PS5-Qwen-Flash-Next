/* SPDX-License-Identifier: MIT */
#include "vmmap_metadata.h"
#include <stdio.h>
#include <stdlib.h>
static unsigned calls;
static int visit(void*c,unsigned n,const struct qwen_vmmap_prefix*p,const unsigned char*path,size_t bytes){
    (void)c;(void)path;(void)bytes;if(n!=calls||p->end<=p->start)abort();++calls;return 1;
}
static void check(int ok){if(!ok)abort();}
int main(void){
    unsigned char data[288]={0};struct qwen_vmmap_prefix a={0};a.bytes=144;a.type=9;a.start=0x4000;a.end=0x8000;
    memcpy(data,&a,sizeof(a));a.start=0x8000;a.end=0xc000;memcpy(data+144,&a,sizeof(a));
    unsigned n=0;calls=0;check(qwen_vmmap_parse(data,sizeof(data),visit,NULL,&n)&&n==2&&calls==2);
    for(unsigned mode=0;mode<9;++mode){
        unsigned char bad[288];memcpy(bad,data,sizeof(bad));struct qwen_vmmap_prefix p;memcpy(&p,bad,sizeof(p));size_t size=sizeof(bad);
        if(mode==0)p.bytes=0;if(mode==1)p.bytes=-8;if(mode==2)p.bytes=136;if(mode==3)p.bytes=143;
        if(mode==4)p.bytes=1168;if(mode==5)p.end=p.start;if(mode==6){p.start=UINT64_MAX;p.end=1;}
        memcpy(bad,&p,sizeof(p));if(mode==7)memset(bad+136,'x',8);if(mode==8)--size;
        calls=0;check(!qwen_vmmap_parse(bad,size,visit,NULL,&n));
    }
    a.start=0x4000;a.end=0x8000;memcpy(data+144,&a,sizeof(a));calls=0;check(!qwen_vmmap_parse(data,sizeof(data),visit,NULL,&n));
    check(!qwen_vmmap_parse(NULL,1,visit,NULL,&n));check(!qwen_vmmap_parse(data,0,visit,NULL,&n));
    check(!qwen_vmmap_parse(data,QWEN_VMMAP_CAPACITY+1,visit,NULL,&n));
    puts("Packed144-byte records, original fields, malformed/truncated/path/span/ordering/bound controls passed");return 0;
}
