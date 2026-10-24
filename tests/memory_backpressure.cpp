// SPDX-License-Identifier: MIT
#include "memory_backpressure.h"
#include <iostream>
#include <vector>
using namespace qwen_app;
static void check(bool x,const char * m){if(!x)throw std::runtime_error(m);}
template<class F> static void rejected(F f){bool failed=false;try{f();}catch(const std::exception&){failed=true;}check(failed,"Unsafe memory admission accepted");}
struct Ops final:MemoryAdmissionOps {
    SystemMemoryObservation value{512ull<<20,16384,10000,1156,900,2000,206};
    std::vector<std::uint32_t> free;
    std::uint64_t clock=1,oversleep=0,pauses=0,observations=0,operations=0;
    bool frozen=false;
    SystemMemoryObservation observe() override {
        ++observations;if(!free.empty()){value.kernel_free=free.front();free.erase(free.begin());}return value;
    }
    std::uint64_t now_ns() override{return clock;}
    void pause_ns(std::uint64_t ns) override {++pauses;if(!frozen)clock+=ns+oversleep;}
    void issue_after(MemoryBackpressure & gate){const auto v=gate.admit(*this);(void)qualified_system_headroom(v);++operations;}
};
int main(){try{
    {Ops ops;MemoryBackpressure g;ops.issue_after(g);check(ops.operations==1&&!ops.pauses,"Healthy admission delayed");
     ops.value.kernel_free=1155;rejected([&]{ops.issue_after(g);});check(ops.operations==1&&!ops.pauses,"Disabled gate changed the old guard");}
    {Ops ops;MemoryBackpressure g;g.enable();ops.free={1100,1155,1156};ops.issue_after(g);
     check(ops.operations==1&&ops.pauses==2&&g.stats().recovered_admissions==1&&g.stats().last_qualified,"Recovery bypassed a fresh exact guard");}
    {Ops ops;MemoryBackpressure g;g.enable();ops.value.kernel_free=1000;rejected([&]{ops.issue_after(g);});
     check(!ops.operations&&ops.pauses==20&&g.stats().wait_ns==MemoryBackpressure::boundary_limit_ns,"Persistent pressure escaped its deadline");
     const auto n=ops.observations;ops.value.kernel_free=2000;rejected([&]{ops.issue_after(g);});check(ops.observations==n,"A failed admission retried");}
    {Ops ops;MemoryBackpressure g(300,500,100);g.enable();ops.free={1000,1000,1156,1000,1000,1156,1000,1000};
     ops.issue_after(g);ops.issue_after(g);rejected([&]{ops.issue_after(g);});check(ops.operations==2&&g.stats().wait_ns==500,"Total budget reset at a new boundary");}
    for(int mode=0;mode<3;++mode){Ops ops;MemoryBackpressure g;g.enable();ops.value.kernel_free=1000;
     if(mode==0)ops.value.page_size=4096;if(mode==1)ops.frozen=true;if(mode==2)ops.oversleep=MemoryBackpressure::boundary_limit_ns;
     rejected([&]{ops.issue_after(g);});check(!ops.operations,"Invalid counters/clock admitted I/O");
     if(mode==0)check(!ops.pauses,"Invalid metadata was polled as recoverable pressure");}
    std::cout<<"Original minimum/reserve, passive recovery, per-boundary/whole-process deadlines and no failed retry passed\n";
}catch(const std::exception & e){std::cerr<<e.what()<<'\n';return 1;}}
