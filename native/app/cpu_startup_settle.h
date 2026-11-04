/* SPDX-License-Identifier: MIT */
#ifndef QWEN_CPU_STARTUP_SETTLE_H
#define QWEN_CPU_STARTUP_SETTLE_H
#include <stdint.h>
struct qwen_cpu_settle_sample {uint32_t free,minimum,reserved,target;};
struct qwen_cpu_settle_ops {
    uint64_t (*now)(void*);
    int (*observe)(void*,struct qwen_cpu_settle_sample*);
    int (*pause_10ms)(void*);
    void (*event)(void*,int,unsigned,const struct qwen_cpu_settle_sample*);
};
/* The reader's minimum+21 admission stays intact. Idle CPU observations add
 * 1152 pages before beginning the unchanged reader; no allocation, source I/O,
 * GPU operation, VM write or launch retry is performed by this finite wait.
 */
static int qwen_cpu_startup_settle(void*ctx,const struct qwen_cpu_settle_ops*ops){
    if(!ops||!ops->now||!ops->observe||!ops->pause_10ms||!ops->event)return 0;
    const uint64_t began=ops->now(ctx);if(!began)return 0;
    struct qwen_cpu_settle_sample first={0},sample={0};
    for(unsigned polls=0;polls<=500;++polls){
        uint64_t stamp=ops->now(ctx);if(!stamp||stamp<began||stamp-began>=5000000000ull)return 0;
        if(!ops->observe(ctx,&sample)||!sample.reserved||sample.reserved>sample.minimum||sample.minimum>=sample.target||
            sample.minimum>UINT32_MAX-1173u||sample.target<sample.minimum+1173u)return 0;
        stamp=ops->now(ctx);if(!stamp||stamp<began||stamp-began>=5000000000ull)return 0;
        if(!polls){first=sample;ops->event(ctx,0,polls,&sample);}
        if(sample.minimum!=first.minimum||sample.reserved!=first.reserved||sample.target!=first.target||sample.free<sample.minimum+21u)return 0;
        if(sample.free>=sample.minimum+1173u){ops->event(ctx,1,polls,&sample);return 1;}
        if(polls==500||ops->pause_10ms(ctx))return 0;
    }
    return 0;
}
#endif
