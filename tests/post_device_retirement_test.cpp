// SPDX-License-Identifier: MIT
#include "post_device_retirement.h"
#include <cassert>
static ps5_ai_arena_kick_stats state;
static ps5_ai_arena_stats owned;
static int snapshots,retirements,logs,failure,change_after;
static int kick(ps5_ai_arena_kick_stats*out){++snapshots;*out=state;if(change_after&&snapshots==2)++out->requested_epoch;return failure==1?-1:0;}
static void owner(ps5_ai_arena_stats*out){*out=owned;}
static int ready(){return failure!=2;}
static int retire(uint64_t epoch){assert(epoch==7);++retirements;return failure==3?0:1;}
static bool journal(){++logs;return failure!=4;}
static void reset(){state={7,7,1,1,0,0,0,0,1};owned={};snapshots=retirements=logs=failure=change_after=0;}
int main(){
    qwen_app::PostDeviceRetirement ops{kick,owner,ready,retire,journal};
    reset();assert(qwen_app::retire_destroyed_device(7,ops)&&snapshots==2&&retirements==1&&logs==1);
    reset();assert(!qwen_app::retire_destroyed_device(0,ops)&&!snapshots&&!retirements);
    for(int which=1;which<=4;++which){reset();failure=which;assert(!qwen_app::retire_destroyed_device(7,ops));}
    reset();state.completed_epoch=6;assert(!qwen_app::retire_destroyed_device(7,ops)&&!retirements);
    reset();state.pending=1;assert(!qwen_app::retire_destroyed_device(7,ops)&&!retirements);
    reset();state.active=1;assert(!qwen_app::retire_destroyed_device(7,ops)&&!retirements);
    reset();state.submit_inflight=1;assert(!qwen_app::retire_destroyed_device(7,ops)&&!retirements);
    reset();state.fault_retained=1;assert(!qwen_app::retire_destroyed_device(7,ops)&&!retirements);
    reset();state.log_healthy=0;assert(!qwen_app::retire_destroyed_device(7,ops)&&!retirements);
    reset();change_after=1;assert(!qwen_app::retire_destroyed_device(7,ops)&&retirements==1&&!logs);
    reset();owned.used_bytes=65536;assert(!qwen_app::retire_destroyed_device(7,ops)&&!logs);
    reset();owned.mapping_uncertain=1;assert(!qwen_app::retire_destroyed_device(7,ops)&&!logs);
    return 0;
}
