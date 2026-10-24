// SPDX-License-Identifier: MIT
#include "direct_integrity.h"
#include "memory_backpressure.h"
#include "profile_clock.h"
#include <iostream>
#include <vector>
using namespace qwen_app;
static void check(bool value,const char *message){if(!value)throw std::runtime_error(message);}
template<class F>static void rejected(F f){bool failed=false;try{f();}catch(const std::exception&){failed=true;}check(failed,"Unsafe startup read accepted");}
struct Observation final:MemoryAdmissionOps {
    SystemMemoryObservation value{512ull<<20,16384,138739,1154,898,2974,206};
    std::vector<std::uint32_t> sequence;
    std::uint64_t clock=1,pauses=0,observations=0;
    SystemMemoryObservation observe()override{
        ++observations;if(!sequence.empty()){value.kernel_free=sequence.front();sequence.erase(sequence.begin());}return value;
    }
    std::uint64_t now_ns()override{return clock;}
    void pause_ns(std::uint64_t ns)override{++pauses;clock+=ns;}
};
static MemoryBackpressure *gate;
static Observation *observation;
static unsigned reads=0;
static std::vector<std::string> stages;
namespace qwen_app {
SystemMemoryObservation admit_native_system_memory(){return gate->admit(*observation);}
}
static void qwen_native_stage(const char *text){stages.emplace_back(text);}
static std::int64_t fixture_pread(int,void*,std::size_t bytes,std::int64_t){++reads;return std::int64_t(bytes);}
// The runner extracts this class verbatim from the actual provider. Host-only
// substitutions supply the read syscall and its already native-checked64-bit type.
#define pread fixture_pread
#define off_t std::int64_t
#include "native_direct_fixture.h"
#undef off_t
#undef pread
static void bind(MemoryBackpressure &g,Observation &ops){gate=&g;observation=&ops;reads=0;stages.clear();}
int main(){try{
    unsigned char output=0;
    {MemoryBackpressure g;g.enable();Observation ops;bind(g,ops);NativeDirect provider(1,false);
     check(provider.read_at(&output,1,0)==1&&reads==1&&!ops.pauses&&stages.empty(),"Healthy production read changed");}
    {MemoryBackpressure g;g.enable();Observation ops;ops.sequence={1066,1153,1154};bind(g,ops);NativeDirect provider(1,true);
     check(provider.read_at(&output,1,0)==1&&reads==1&&ops.pauses==2&&g.stats().recovered_admissions==1,"Transient startup pressure did not recover before the single read");
     check(stages==std::vector<std::string>{"startup_SELF_read_before_native_call","startup_SELF_read_native_call_returned"},"Read markers did not surround exactly one returned call");}
    {MemoryBackpressure g;g.enable();Observation ops;ops.value.kernel_free=1066;bind(g,ops);NativeDirect provider(1,true);
     rejected([&]{provider.read_at(&output,1,0);});check(!reads&&stages.empty()&&ops.pauses==200&&g.stats().wait_ns==20000000000ull,"Persistent pressure started I/O or escaped the original boundary");
     auto n=ops.observations;ops.value.kernel_free=5000;rejected([&]{provider.read_at(&output,1,0);});check(!reads&&ops.observations==n,"Failed startup admission retried");}
    {MemoryBackpressure g;g.enable();Observation ops;ops.value.page_size=4096;bind(g,ops);NativeDirect provider(1,false);
     rejected([&]{provider.read_at(&output,1,0);});check(!reads&&!ops.pauses&&stages.empty(),"Invalid counter metadata entered polling or I/O");}
    {MemoryBackpressure g(300,500,100);g.enable();Observation ops;ops.sequence={1066,1066,1154,1066,1066,1154,1066,1066};bind(g,ops);NativeDirect provider(1,false);
     (void)admit_native_system_memory();check(!reads&&ops.pauses==2,"Initial boundary started I/O");
     check(provider.read_at(&output,1,0)==1&&reads==1,"Completed read boundary failed");
     rejected([&]{provider.read_at(&output,1,0);});check(reads==1&&g.stats().wait_ns==500,"Startup boundaries reset the shared process wait budget");}
    std::cout<<"Actual native provider: original1154-page predicate, recovery, no premature read, quarantine, invalid counters and shared wait budget passed\n";
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
