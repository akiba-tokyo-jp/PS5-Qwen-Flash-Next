/* SPDX-License-Identifier: MIT
 * Execute the actual driver journal with deterministic CPU filesystem stubs. */
#include <stdbool.h>
#include <stdint.h>
#include <stdatomic.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <time.h>
#include <unistd.h>
#include <assert.h>
#include "journal_metrics.h"
static int arena_fd=7;
static atomic_bool arena_log_healthy=ATOMIC_VAR_INIT(true);
static atomic_flag arena_log_mutex=ATOMIC_FLAG_INIT;
static unsigned writes,syncs;
static size_t written;
static int mode;
static uint64_t tick;
static ssize_t mock_write(int fd,const void * p,size_t n) {
    assert((fd==7||fd==2)&&p&&n);writes++;
    if(mode==3&&writes==1){errno=EINTR;return -1;}
    if(mode==2&&n>3)n=3;
    written+=n;return (ssize_t)n;
}
static int mock_sync(int fd){assert(fd==7);syncs++;return mode==1?-1:0;}
static int mock_clock(clockid_t id,struct timespec *out){(void)id;*out=(struct timespec){.tv_sec=1,.tv_nsec=(long)(++tick)};return 0;}
#define write mock_write
#define fsync mock_sync
#define clock_gettime mock_clock
#include "driver_journal_impl.inc"
#undef write
#undef fsync
#undef clock_gettime
bool ps5_ai_native_journal_debug_enabled(void){return true;}
static void reset(int scenario){
    mode=scenario;writes=syncs=0;written=0;tick=0;
    arena_journal_bytes=0;arena_terminal_reported=false;arena_journal_totals=(struct ps5_ai_native_arena_journal_stats){0};
    arena_routine_records=arena_routine_bytes=arena_last_sync_ns=0;arena_sync_time_valid=false;
    atomic_store(&arena_log_healthy,true);atomic_flag_clear(&arena_log_mutex);
}
int main(void){
    reset(0);assert(ps5_ai_arena_trace("BEFORE owned operation")&&writes==1&&syncs==1&&arena_journal_totals.records==1);
    reset(2);assert(ps5_ai_arena_trace("partial writes")&&writes>1&&written==15&&syncs==1);
    reset(3);assert(ps5_ai_arena_trace("interrupted")&&writes==2&&written==12&&syncs==1);
    reset(0);arena_journal_bytes=(UINT64_C(64)<<20)-2048;
    assert(!ps5_ai_arena_trace("cannot exceed capacity")&&!atomic_load(&arena_log_healthy)&&arena_terminal_reported);
    unsigned once_writes=writes,once_syncs=syncs;size_t once_bytes=written;
    for(unsigned i=0;i<100;i++)assert(!ps5_ai_arena_trace("failed state stays bounded"));
    assert(writes==once_writes&&syncs==once_syncs&&written==once_bytes&&written<2048);
    reset(1);assert(!ps5_ai_arena_trace("sync fails"));once_writes=writes;once_syncs=syncs;
    assert(!ps5_ai_arena_trace("cannot resume"));assert(writes==once_writes&&syncs==once_syncs);
    reset(0);assert(ps5_ai_arena_trace_routine("routine"));assert(ps5_ai_native_arena_journal_checkpoint());
    puts("Actual journal preserves partial/interrupted writes, reserves terminal space and never retries terminal output after failure; CPU API stubs only");
    return 0;
}
