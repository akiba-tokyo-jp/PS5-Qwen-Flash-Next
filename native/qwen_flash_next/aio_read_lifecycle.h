/* SPDX-License-Identifier: MIT */
#pragma once
#include "aio_read_abi.h"
struct qwen_aio_ops {
    int (*submit)(struct qwen_aio_read *,int,int,int *);
    int (*wait)(int,int *,uint32_t *);
    int (*retire)(int,int *);
};
/* 1: terminal bytes checked and ID retired exactly once; 0: known refusal or
 * terminal read failure; -1: uncertain ownership, retain everything and stop.
 * There is no cancellation, repeated delete, resubmission or unbounded wait. */
static int qwen_aio_complete(const struct qwen_aio_ops *ops,
        struct qwen_aio_read *requests,unsigned count,int expect_invalid,int *pending) {
    const uint64_t canary=UINT64_C(0x8f37d125c096ea4b);
    struct {uint64_t a;int value;uint32_t pad;uint64_t b;} id={canary,0,0,canary};
    if(!ops||!ops->submit||!ops->wait||!ops->retire||!requests||!pending||*pending||
       !count||count>2||(expect_invalid&&count!=1))return 0;
    for(unsigned i=0;i<count;++i)
        if(!requests[i].buffer||!requests[i].result||!requests[i].bytes||requests[i].bytes>3293184||
           requests[i].offset<0||requests[i].pad||requests[i].result->state||
           (expect_invalid?requests[i].fd!=-1:requests[i].fd<0))return 0;
    *pending=1;
    int rc=ops->submit(requests,(int)count,2,&id.value);
    if(id.a!=canary||id.b!=canary)return -1;
    if(rc<0) {
        if(id.value)return -1;
        for(unsigned i=0;i<count;++i)if(requests[i].result->state)return -1;
        *pending=0;return 0;
    }
    if(rc||id.value<=0)return -1;
    struct {uint64_t a;int value;uint32_t pad;uint64_t b;} state={canary,0,0,canary};
    struct {uint64_t a;uint32_t value,pad;uint64_t b;} timeout={canary,10000000,0,canary};
    rc=ops->wait(id.value,&state.value,&timeout.value);
    const unsigned terminal=(unsigned)state.value&0xffff;
    if(rc||state.a!=canary||state.b!=canary||timeout.a!=canary||timeout.b!=canary||
       (terminal!=3&&terminal!=4))return -1;
    int ok=1;
    for(unsigned i=0;i<count;++i) {
        const unsigned done=requests[i].result->state&0xffff;
        if(done!=3&&done!=4)return -1;
        if(expect_invalid)ok&=requests[i].result->value<0;
        else ok&=done==3&&requests[i].result->value==(int64_t)requests[i].bytes;
    }
    struct {uint64_t a;int value;uint32_t pad;uint64_t b;} retired={canary,-1,0,canary};
    rc=ops->retire(id.value,&retired.value);
    if(rc||retired.value||retired.a!=canary||retired.b!=canary)return -1;
    *pending=0;return ok;
}
