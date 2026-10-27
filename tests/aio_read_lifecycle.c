/* SPDX-License-Identifier: MIT */
#include "aio_read_lifecycle.h"
#include <stdio.h>
#include <string.h>
static unsigned mode,submits,waits,retires;
static struct qwen_aio_read *live;
static int submit(struct qwen_aio_read *r,int count,int priority,int *id) {
    ++submits;live=r;if(count!=1||priority!=2)return -1;
    if(mode==1)return -9;
    *id=7;if(mode==2)return -9;
    if(mode==3)*id=0;
    return 0;
}
static int wait_once(int id,int *state,uint32_t *timeout) {
    ++waits;if(id!=7||*timeout!=10000000)return -1;
    *state=mode==4?2:3;
    live->result->state=mode==5?2:3;
    live->result->value=mode==6?4:(mode==10?-9:(int64_t)live->bytes);
    if(mode==10){*state=4;live->result->state=4;}
    return mode==7?-60:0;
}
static int retire(int id,int *result) {
    ++retires;if(id!=7)return -1;
    *result=mode==8?-1:0;return mode==9?-1:0;
}
int main(void) {
    const struct qwen_aio_ops ops={submit,wait_once,retire};unsigned controls=0;
    for(mode=0;mode<=10;++mode) {
        unsigned char target[16];struct qwen_aio_result result={0};
        struct qwen_aio_read r={0,sizeof(target),target,&result,mode==10?-1:4,0};int pending=0;
        submits=waits=retires=0;
        int got=qwen_aio_complete(&ops,&r,1,mode==10,&pending);
        int expected=(mode==0||mode==10)?1:((mode==1||mode==6)?0:-1);
        if(got!=expected||submits!=1||pending!=(expected==-1))return 1;
        if(retires!=(mode==0||mode==6||mode==8||mode==9||mode==10))return 2;
        if(waits!=(mode!=1&&mode!=2&&mode!=3))return 3;
        ++controls;
    }
    struct qwen_aio_result result={0};char target[16];
    struct qwen_aio_read r={0,16,target,&result,4,0};
    for(unsigned n=0;n<5;++n) {
        int pending=n==0;struct qwen_aio_read bad=r;
        if(n==1)bad.result=NULL;if(n==2)bad.fd=-1;if(n==3)bad.bytes=3293185;if(n==4)bad.offset=-1;
        submits=waits=retires=0;
        if(qwen_aio_complete(&ops,&bad,1,0,&pending)||submits||waits||retires)return 4;
        ++controls;
    }
    printf("{\"actual_lifecycle_controls\":%u,\"unknown_owners_never_retired\":true,\"PS5_operations\":0}\n",controls);
    return 0;
}
