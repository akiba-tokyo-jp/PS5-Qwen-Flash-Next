/* SPDX-License-Identifier: MIT
 * In-memory clock/SHA failure injection; no native execution or file changes.
 */
#define QWEN_HASH_PROBE_HOST_STUBS 1
#define main model_hash_probe_entry
#include "../native/qwen_flash_next/model_hash_probe.c"
#undef main
#include <stdlib.h>

static unsigned checks,clock_calls;
static int failed_clock,clobber_clock,reverse_clock,invalid_nsec,negative_sec,frozen_clock;
static uint64_t step_ns;
static void check(int value){++checks;if(!value){fprintf(stderr,"Hash probe check %u failed\n",checks);exit(1);}}
static void reset(void){clock_calls=0;failed_clock=clobber_clock=reverse_clock=invalid_nsec=negative_sec=frozen_clock=0;step_ns=UINT64_C(1000000000);}
int hp_clock_gettime(int id,struct timespec *out){
    if(id!=CLOCK_MONOTONIC||failed_clock)return -1;
    uint64_t value=frozen_clock?0:step_ns*clock_calls;
    if(reverse_clock&&clock_calls>1)value=0;
    ++clock_calls;out->tv_sec=(time_t)(value/UINT64_C(1000000000));out->tv_nsec=(long)(value%UINT64_C(1000000000));
    if(invalid_nsec)out->tv_nsec=1000000000;
    if(negative_sec)out->tv_sec=-1;
    if(clobber_clock){HashProbeClock *clock=(HashProbeClock*)((char*)out - offsetof(HashProbeClock,value));clock->after=0;}
    return 0;
}
int hp_open(const char *path,int flags,...){(void)path;(void)flags;return -1;}
int hp_close(int fd){(void)fd;return 0;}
unsigned hp_getuid(void){return 1;}
unsigned hp_geteuid(void){return 0;}
int hp_fsync(int fd){(void)fd;return 0;}
FILE *hp_fdopen(int fd,const char *mode){(void)fd;(void)mode;return NULL;}
int hp_fileno(FILE *log){(void)log;return 0;}
int main(void){
    HashProbeResult result;uint64_t now;
    reset();check(hash_probe(&result,PROBE_SHA256));check(result.passes==5&&result.bytes==5ull*PROBE_BYTES);
    check(result.elapsed_ns==UINT64_C(10000000000));
    reset();check(!hash_probe(&result,"0000000000000000000000000000000000000000000000000000000000000000"));check(result.bytes==0);
    reset();failed_clock=1;check(!hash_probe(&result,PROBE_SHA256));check(result.bytes==0);
    reset();clobber_clock=1;check(!observe_time(&now));
    reset();invalid_nsec=1;check(!observe_time(&now));
    reset();negative_sec=1;check(!observe_time(&now));
    reset();clock_calls=1;reverse_clock=1;check(!hash_probe(&result,PROBE_SHA256));
    reset();step_ns=UINT64_C(20000000000);check(!hash_probe(&result,PROBE_SHA256));check(result.bytes==0);
    reset();step_ns=UINT64_C(2000000000);check(!hash_probe(&result,PROBE_SHA256));check(result.passes<4);
    reset();check(!hash_probe(&result,NULL));check(!hash_probe(&result,"not a digest"));
    printf("CPU hash synthetic payload and guarded timer: %u checks passed\n",checks);
    return 0;
}
