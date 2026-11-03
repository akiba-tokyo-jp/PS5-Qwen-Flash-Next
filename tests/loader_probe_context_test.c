/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include "loader_probe_context.h"
int main(void){
    const char valid[]="{\"schema\":\"ps5-qwen-CPU-loader-v1\",\"run_id\":\"0123456789abcdef0123456789abcdef\",\"SELF_bytes\":12345,\"SELF_sha256\":\"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\",\"heap_bytes\":8388608}\n";
    char v[512];struct loader_probe_context c;
    assert(loader_probe_parse(valid,strlen(valid),&c)&&c.bytes==12345&&c.heap==8388608);
    strcpy(v,valid);v[42]='G';assert(!loader_probe_parse(v,strlen(v),&c));
    strcpy(v,valid);v[8]='X';assert(!loader_probe_parse(v,strlen(v),&c));
    strcpy(v,valid);strcat(v,"x");assert(!loader_probe_parse(v,strlen(v),&c));
    strcpy(v,valid);v[strlen(v)-1]=0;assert(!loader_probe_parse(v,strlen(v),&c));
    strcpy(v,valid);v[30]=0;assert(!loader_probe_parse(v,sizeof(valid)-1,&c));
    assert(!loader_probe_parse(valid,strlen(valid),NULL));
    assert(!loader_probe_parse(NULL,1,&c));
    return 0;
}
