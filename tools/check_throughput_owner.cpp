// SPDX-License-Identifier: MIT
#include "owner_retirement_certificate.h"
#include <cassert>
#include <iostream>
int main(){
    using qwen_throughput::OwnerRetirementCertificate;
    int frontend=0,other=0;ps5_ai_arena_stats state{};
    state.reserved_bytes=state.used_bytes=65536;state.peak_used_bytes=131072;
    state.live_allocations=4;state.allocation_attempts=12;state.physical_owned=state.mapping_owned=1;
    OwnerRetirementCertificate c{&frontend,7,40,10,state};unsigned checks=0;
    const auto denied=[&](ps5_ai_arena_stats changed){++checks;assert(!c.matches(&frontend,7,40,10,changed));};
    assert(c.matches(&frontend,7,40,10,state));++checks;
    assert(c.matches(&frontend,7,41,11,state));++checks;
    assert(!c.matches(&other,7,40,10,state));++checks;
    assert(!c.matches(&frontend,8,40,10,state));++checks;
    assert(!c.matches(&frontend,7,39,10,state));++checks;
    assert(!c.matches(&frontend,7,40,9,state));++checks;
    assert(!c.matches(&frontend,0,40,10,state));++checks;
    assert(!c.matches(&frontend,7,0,10,state));++checks;
    assert(!c.matches(&frontend,7,40,0,state));++checks;
    auto changed=state;changed.allocation_attempts++;denied(changed); // Equal-byte free/reallocate ABA.
    changed=state;changed.live_allocations--;denied(changed); // New metadata-only retirement.
    changed=state;changed.used_bytes-=16384;denied(changed);
    changed=state;changed.reserved_bytes-=16384;denied(changed);
    changed=state;changed.peak_used_bytes++;denied(changed);
    changed=state;changed.denied_allocations++;denied(changed);
    changed=state;changed.physical_owned=0;denied(changed);
    changed=state;changed.mapping_owned=0;denied(changed);
    changed=state;changed.mapping_uncertain=1;denied(changed);
    changed=state;changed.gpu_fault_retained=1;denied(changed);
    changed=state;changed.global_capacity_measured=1;denied(changed);
    changed=state;changed.allocation_attempts=UINT64_MAX;denied(changed);
    OwnerRetirementCertificate cold{};assert(!cold.matches(&frontend,7,40,10,state));++checks;
    std::cout<<"{\"completed\":true,\"certificate_checks\":"<<checks<<",\"host_inference\":false}\n";
}
