// SPDX-License-Identifier: MIT
#include "retained_completed_device.h"
#include <cstdio>
#include <cstdlib>
namespace {
ps5_ai_arena_kick_stats state{};ps5_ai_arena_stats ownership{};
bool journal_ok=true,advance=false;unsigned reads=0;
int kick(ps5_ai_arena_kick_stats*out){*out=state;if(advance&&++reads>1)++out->requested_epoch;return 0;}
void owner(ps5_ai_arena_stats*out){*out=ownership;}
bool journal(){return journal_ok;}
void need(bool value){if(!value)std::abort();}
void reset(){state={};ownership={};journal_ok=true;advance=false;reads=0;
    state.initialized=state.thread_started=state.log_healthy=1;state.requested_epoch=state.completed_epoch=7;
    ownership.reserved_bytes=4096;ownership.used_bytes=2048;ownership.live_allocations=1;
    ownership.physical_owned=ownership.mapping_owned=1;}
}
int main(){
    const qwen_app::RetainedDeviceOps ops{kick,owner,journal};
    reset();qwen_app::RetainedCompletedDevice positive;
    need(qwen_app::retain_completed_device(1,2,7,positive,ops)&&positive.held&&positive.device==1&&positive.instance==2&&
         positive.epoch==7&&positive.owner.physical_owned&&!positive.owner.global_capacity_measured);
    unsigned negatives=0;
    for(unsigned fault=0;fault<17;++fault){reset();qwen_app::RetainedCompletedDevice lease;
        std::uintptr_t device=1,instance=2;std::uint64_t epoch=7;
        switch(fault){
        case 0:device=0;break;case 1:instance=0;break;case 2:epoch=0;break;
        case 3:lease.held=true;break;case 4:state.pending=1;break;case 5:state.active=1;break;
        case 6:state.submit_inflight=1;break;case 7:state.fault_retained=1;break;
        case 8:state.log_healthy=0;break;case 9:state.requested_epoch=8;break;
        case 10:state.completed_epoch=6;break;case 11:ownership.mapping_uncertain=1;break;
        case 12:ownership.gpu_fault_retained=1;break;case 13:ownership.physical_owned=0;break;
        case 14:journal_ok=false;break;case 15:advance=true;break;
        case 16:ownership.global_capacity_measured=1;break;
        }
        need(!qwen_app::retain_completed_device(device,instance,epoch,lease,ops));++negatives;
        need(ownership.live_allocations==1&&ownership.reserved_bytes==4096);
    }
    reset();ownership={};qwen_app::RetainedCompletedDevice empty;
    need(qwen_app::retain_completed_device(3,4,7,empty,ops)&&empty.held&&!empty.owner.used_bytes);
    std::printf("{\"completed\":true,\"positive_controls\":2,\"negative_controls\":%u,\"device_destroy_calls\":0,\"driver_retire_calls\":0,\"PS5_operations\":0}\n",negatives);
}
