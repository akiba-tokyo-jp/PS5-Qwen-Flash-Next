/* SPDX-License-Identifier: MIT */
#include "vmmap_metadata.h"
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#define CTL_KERN 1
#define KERN_PROC 14
#define KERN_PROC_VMMAP 32
static unsigned mode,queries,entries;
static int report(const char*format,...){return !(mode==9&&!strcmp(format,"VMMAP_DATA_BEFORE"));}
static int region(void*c,unsigned n,const struct qwen_vmmap_prefix*p,const unsigned char*path,size_t size){(void)c;(void)n;(void)p;(void)path;(void)size;++entries;return 1;}
static int sysctl(const int*m,unsigned count,void*data,size_t*bytes,const void*new_data,size_t new_bytes){
    if(count!=4||m[0]!=1||m[1]!=14||m[2]!=32||m[3]!=123||new_data||new_bytes)abort();++queries;
    if(!data){
        if(mode==1){errno=2;return -1;}*bytes=mode==2?0:mode==3?QWEN_VMMAP_CAPACITY+1:144;return 0;
    }
    if(*bytes!=QWEN_VMMAP_CAPACITY||queries!=2)abort();
    struct qwen_vmmap_prefix p={0};p.bytes=144;p.type=9;p.start=0x4000;p.end=0x8000;
    memset(data,0,144);memcpy(data,&p,sizeof(p));*bytes=144;
    if(mode==4){errno=4;return -1;}if(mode==5)*bytes=QWEN_VMMAP_CAPACITY+1;
    if(mode==6)((unsigned char*)data)[QWEN_VMMAP_CAPACITY]^=1;
    if(mode==7)((unsigned char*)data)[-1]^=1;if(mode==8)((struct qwen_vmmap_prefix*)data)->bytes=0;
    return 0;
}
#include "actual_vmmap_query.h"
static void check(int ok){if(!ok)abort();}
int main(void){for(mode=0;mode<10;++mode){
    queries=entries=0;vmmap_pending=vmmap_calls=vmmap_supported=vmmap_parsed=0;vmmap_records=0;
    int result=vmmap_once(123);check(!vmmap_pending&&queries<=2&&vmmap_calls==(int)queries);
    if(mode==0)check(result&&vmmap_parsed&&vmmap_records==1&&entries==1&&queries==2);
    else check(!vmmap_parsed&&!entries);
    if(mode==1||mode==2||mode==3)check(result&&queries==1);
    if(mode==6||mode==7||mode==9)check(!result);
    if(mode==9)check(queries==1);
}puts("Actual VM map query: supported/unsupported/bounds/short/error/canary/journal controls, no retries, at most two calls passed");return 0;}
