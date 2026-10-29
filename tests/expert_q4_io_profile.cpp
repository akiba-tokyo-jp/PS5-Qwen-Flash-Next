// SPDX-License-Identifier: MIT
#include "expert_q4_io_profile.h"
#include <cassert>
#include <iostream>
struct Counters {std::uint64_t bytes=100,physical_read_bytes=1000,physical_read_calls=2,read_ns=30,chunks=4,completed_windows=4;};
int main(){
    qwen_app::ExpertQ4IOProfile p;Counters a;
    p.begin(nullptr,0,0,a);p.end(a);assert(!p.live&&p.totals[0].logical==0);
    p.enabled=true;p.begin("token_embd.weight",1,5120,a);
    auto b=a;b.bytes+=5120;b.physical_read_bytes+=16384;b.physical_read_calls+=1;b.read_ns+=1000;b.chunks++;b.completed_windows++;
    p.end(b);assert(p.totals[0].logical==5120&&p.totals[0].physical==16384&&p.totals[0].wait_ns==1000);
    p.begin("per_layer_token_embd.weight",16,320,b);auto c=b;c.bytes+=5120;c.physical_read_bytes+=16*16384;c.physical_read_calls+=16;c.read_ns+=2000;
    p.end(c);assert(p.totals[1].rows==16&&p.totals[1].logical==5120&&p.totals[1].calls==16);
    unsigned refused=0;auto reject=[&](auto f){try{f();return false;}catch(const std::exception&){++refused;return true;}};
    qwen_app::ExpertQ4IOProfile duplicate;duplicate.enabled=true;duplicate.begin("token_embd.weight",1,5120,a);
    assert(reject([&]{duplicate.begin("token_embd.weight",1,5120,a);}));
    qwen_app::ExpertQ4IOProfile missing;missing.enabled=true;assert(reject([&]{missing.end(a);}));
    qwen_app::ExpertQ4IOProfile short_read;short_read.enabled=true;short_read.begin("token_embd.weight",1,5120,a);
    auto short_value=b;--short_value.bytes;assert(reject([&]{short_read.end(short_value);}));
    qwen_app::ExpertQ4IOProfile pending;pending.enabled=true;auto pending_value=a;++pending_value.chunks;
    assert(reject([&]{pending.begin("token_embd.weight",1,5120,pending_value);}));
    qwen_app::ExpertQ4IOProfile rolled;rolled.enabled=true;rolled.begin("token_embd.weight",1,5120,a);
    auto backwards=b;backwards.read_ns=29;assert(reject([&]{rolled.end(backwards);}));
    std::cout<<"{\"CPU_row_attribution_controls_passed\":true,\"invalid_scopes_refused\":"<<refused<<",\"GPU_operations\":0}\n";
}
