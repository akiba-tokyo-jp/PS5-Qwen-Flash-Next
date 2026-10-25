// SPDX-License-Identifier: MIT
#include "boundary_memory_trace.h"
#include <cassert>
#include <stdexcept>
#include <string>
int main() {
    qwen_app::BoundaryMemoryTrace trace;
    unsigned calls=0;
    for(unsigned i=1;i<=80;++i)trace.record("completed_boundary",[&](auto &s){
        ++calls;s.kernel_free=calls;s.monotonic_ns=calls;s.valid=true;
    });
    assert(calls==80&&trace.total()==80&&trace.size()==64&&!trace.invalid());
    for(unsigned i=0;i<64;++i)assert(trace.at(i).sequence==i+17&&trace.at(i).kernel_free==i+17);
    trace.record("failed_observation",[](auto &){throw std::runtime_error("Unavailable counter");});
    assert(trace.invalid()&&trace.total()==81&&!trace.at(63).valid);
    assert(trace.at(62).sequence==80&&trace.at(62).valid);
    const std::string too_long(64,'x');
    trace.record(too_long.c_str(),[&](auto &){++calls;});
    trace.record(nullptr,[&](auto &){++calls;});
    assert(trace.total()==81&&calls==80);
}
