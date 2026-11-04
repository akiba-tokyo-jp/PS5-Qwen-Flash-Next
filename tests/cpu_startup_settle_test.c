/* SPDX-License-Identifier: MIT */
#include "cpu_startup_settle.h"
#include <stdio.h>
#include <stdlib.h>
struct mock {uint64_t ns;unsigned samples,sleeps,events,recover_at;int mode;};
enum {READY,RECOVER,NEVER,INVALID,ZERO_CLOCK,BACKWARD,SLEEP_ERROR,OVERSLEEP,SLOW_SAMPLE,BELOW_FLOOR,GEOMETRY,FROZEN,EXACT_DEADLINE,OVERFLOW_GEOMETRY,COUNT};
#define CHECK(v) do{if(!(v)){fprintf(stderr,"failed line %d mode %d\n",__LINE__,m.mode);exit(1);}}while(0)
static uint64_t now(void*v){struct mock*m=v;return m->mode==ZERO_CLOCK?0:m->ns;}
static int sample(void*v,struct qwen_cpu_settle_sample*s){
    struct mock*m=v;++m->samples;*s=(struct qwen_cpu_settle_sample){1000,898,206,2974};
    if(m->mode==READY||(m->mode==RECOVER&&m->sleeps>=m->recover_at))s->free=2200;
    if(m->mode==BELOW_FLOOR)s->free=918;
    if(m->mode==GEOMETRY&&m->samples>1)++s->target;
    if(m->mode==OVERFLOW_GEOMETRY){s->minimum=UINT32_MAX-3;s->target=UINT32_MAX;}
    if(m->mode==SLOW_SAMPLE){m->ns+=5000000000ull;s->free=2200;}
    if(m->mode==EXACT_DEADLINE&&m->samples==2){m->ns+=4990000000ull;s->free=2200;}
    return m->mode!=INVALID;
}
static int pause_10ms(void*v){
    struct mock*m=v;++m->sleeps;
    if(m->mode==BACKWARD)m->ns=0;
    else if(m->mode==OVERSLEEP)m->ns+=6000000000ull;
    else if(m->mode!=FROZEN)m->ns+=10000000ull;
    return m->mode==SLEEP_ERROR;
}
static void event(void*v,int kind,unsigned polls,const struct qwen_cpu_settle_sample*s){
    struct mock*m=v;(void)polls;(void)s;m->events|=1u<<kind;
}
int main(void){
    const struct qwen_cpu_settle_ops ops={now,sample,pause_10ms,event};
    for(int mode=0;mode<COUNT;++mode){
        struct mock m={1,0,0,0,3,mode};int result=qwen_cpu_startup_settle(&m,&ops);
        CHECK(result==(mode==READY||mode==RECOVER));CHECK(m.sleeps<=500&&m.samples<=501);
        if(mode==READY)CHECK(m.samples==1&&m.sleeps==0&&m.events==3);
        if(mode==RECOVER)CHECK(m.samples==4&&m.sleeps==3&&m.events==3);
        if(mode==INVALID||mode==ZERO_CLOCK||mode==BELOW_FLOOR||mode==SLOW_SAMPLE)CHECK(!m.sleeps);
        if(mode==OVERSLEEP)CHECK(m.samples==1&&m.sleeps==1);
        if(mode==FROZEN)CHECK(m.samples==501&&m.sleeps==500);
    }
    printf("{\"completed\":true,\"cases\":%d,\"unchanged_reader_floor_preserved\":true,\"bounded_passive_wait\":true,\"PS5_operations\":0}\n",COUNT);
    return 0;
}
