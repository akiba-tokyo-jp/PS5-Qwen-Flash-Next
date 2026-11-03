/* SPDX-License-Identifier: MIT */
#ifndef QWEN_LOADER_PROBE_CONTEXT_H
#define QWEN_LOADER_PROBE_CONTEXT_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>
struct loader_probe_context {char run[33],sha[65];unsigned long long bytes,heap;};
static int loader_probe_parse(const char*text,size_t n,struct loader_probe_context*c){
    int end=0;char canonical[320];
    if(!text||!c||!n||n>=sizeof(canonical)||memchr(text,0,n)||text[n])return 0;
    memset(c,0,sizeof(*c));
    if(sscanf(text,"{\"schema\":\"ps5-qwen-CPU-loader-v1\",\"run_id\":\"%32[0-9a-f]\",\"SELF_bytes\":%llu,\"SELF_sha256\":\"%64[0-9a-f]\",\"heap_bytes\":%llu}%n",
        c->run,&c->bytes,c->sha,&c->heap,&end)!=4||strlen(c->run)!=32||strlen(c->sha)!=64||
        c->bytes==0||c->bytes>(4u<<20)||(c->heap!=(8u<<20)&&c->heap!=UINT64_MAX)||end<=0)return 0;
    int size=snprintf(canonical,sizeof(canonical),"{\"schema\":\"ps5-qwen-CPU-loader-v1\",\"run_id\":\"%s\",\"SELF_bytes\":%llu,\"SELF_sha256\":\"%s\",\"heap_bytes\":%llu}\n",
        c->run,c->bytes,c->sha,c->heap);
    return size>0&&(size_t)size==n&&!memcmp(canonical,text,n);
}
#endif
