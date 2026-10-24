// SPDX-License-Identifier: MIT
// Include the independently qualified PS5 priority layout before kinfo_proc.
#include <sys/types.h>
#include "../diagnostics/sys/priority.h"
#include <sys/user.h>
#include <sys/sysctl.h>
#include <sys/resource.h>
#include <unistd.h>
#include <pthread.h>
#include <atomic>
#include <cerrno>
#include <time.h>
#include <nlohmann/json.hpp>
#include "source_contention.h"
#include "system_memory.h"
extern "C" int pthread_getthreadid_np(void);
namespace qwen_app {
namespace {
constexpr std::uint64_t canary = 0x7b527b527b527b52ull;
static_assert(sizeof(kinfo_proc) == 1096, "Qualified native PID metadata ABI");
std::uint64_t clock_ns(clockid_t kind, bool required) {
    struct {std::uint64_t a;timespec t;std::uint64_t b;} g{canary,{},canary};
    if (clock_gettime(kind,&g.t) || g.a!=canary || g.b!=canary || g.t.tv_sec<0 ||
        g.t.tv_nsec<0 || g.t.tv_nsec>=1000000000) {
        if (required) throw std::runtime_error("A diagnostic monotonic clock is unavailable");
        return 0;
    }
    return std::uint64_t(g.t.tv_sec)*1000000000ull+std::uint64_t(g.t.tv_nsec);
}
bool thread_usage(rusage & out) {
    struct {std::uint64_t a[2];unsigned char bytes[512];std::uint64_t b[2];} g{};
    g.a[0]=g.a[1]=g.b[0]=g.b[1]=canary;
    static_assert(sizeof(rusage)<=sizeof(g.bytes),"Bounded thread usage ABI");
    if (getrusage(RUSAGE_THREAD,reinterpret_cast<rusage *>(g.bytes)) ||
        g.a[0]!=canary || g.a[1]!=canary || g.b[0]!=canary || g.b[1]!=canary) return false;
    std::memcpy(&out,g.bytes,sizeof(out));return true;
}
std::uint64_t page_sample(const SourceReadRequest & r,std::uint64_t bytes) {
    if (bytes<8 || bytes>r.bytes) throw std::runtime_error("Invalid completed diagnostic byte count");
    std::uint64_t hash=1469598103934665603ull,value=0;
    const auto * p=static_cast<const unsigned char *>(r.target);
    for (std::uint64_t i=0;i+8<=bytes;i+=16384) {std::memcpy(&value,p+i,8);hash=(hash^value)*1099511628211ull;}
    std::memcpy(&value,p+bytes-8,8);return (hash^value)*1099511628211ull;
}
}
struct SourceContentionMonitor::Impl {
    struct Read {std::uint64_t begin=0,end=0,cpu=0;long voluntary=0,involuntary=0;std::int64_t got=-1;int error=0;};
    struct Row {unsigned round=0,mode=0,index=0;CompletedSourcePair key{};
        std::array<SourceReadRequest,2> requests{};std::array<std::uint64_t,2> expected{};
        std::array<Read,2> reads{};SystemMemoryObservation before{},after{};
        std::uint64_t begin=0,end=0;};
    struct Wait {unsigned phase=0,count=0;char name[WMESGLEN+1]{};};
    std::array<Wait,128> waits{};
    unsigned wait_count=0,queries=0,query_errors=0,unmatched=0;
    std::atomic<bool> sampling{false},ready{false},pair_active{false},observe_pair{false};
    std::atomic<unsigned> phase{0};
    std::thread observer;
    int producer_tid=0;
    bool started=false,finished=false;
    Row current{};
    std::vector<Row> rows;
    std::array<std::array<std::uint64_t,2>,32> reference{};
    std::array<bool,32> reference_ready{};
    void observe() noexcept {
        ready.store(true,std::memory_order_release);
        while (sampling.load(std::memory_order_acquire)) {
            if (observe_pair.load(std::memory_order_acquire)) {
                struct {std::uint64_t a[2];unsigned char bytes[4096];std::uint64_t b[2];} g{};
                g.a[0]=g.a[1]=g.b[0]=g.b[1]=canary;std::size_t bytes=sizeof(g.bytes);
                int mib[]={CTL_KERN,KERN_PROC,KERN_PROC_PID,getpid()};++queries;
                const int rc=sysctl(mib,4,g.bytes,&bytes,nullptr,0);
                if (rc || bytes!=sizeof(kinfo_proc) || g.a[0]!=canary || g.a[1]!=canary ||
                    g.b[0]!=canary || g.b[1]!=canary) ++query_errors;
                else {
                    kinfo_proc k{};std::memcpy(&k,g.bytes,sizeof(k));
                    if (k.ki_structsize!=sizeof(k) || k.ki_pid!=getpid() || k.ki_tid!=producer_tid ||
                        !std::memchr(k.ki_wmesg,0,sizeof(k.ki_wmesg))) ++unmatched;
                    else {
                        const auto p=phase.load(std::memory_order_acquire);unsigned i=0;
                        for (;i<wait_count;++i) if (waits[i].phase==p && !std::strcmp(waits[i].name,k.ki_wmesg)) break;
                        if (i==wait_count && i<waits.size()) {waits[i].phase=p;std::strcpy(waits[i].name,k.ki_wmesg);++wait_count;}
                        if (i<waits.size()) ++waits[i].count;else ++query_errors;
                    }
                }
            }
            if (usleep(1000)) {++query_errors;return;}
        }
    }
};
SourceContentionMonitor::SourceContentionMonitor():impl_(std::make_unique<Impl>()) {}
SourceContentionMonitor::~SourceContentionMonitor() = default;
bool SourceContentionMonitor::active() const {return impl_->pair_active.load(std::memory_order_acquire);}
void SourceContentionMonitor::start() {
    auto & p=*impl_;
    if (p.started) throw std::runtime_error("The native source diagnostic may start only once");
    p.started=true;p.producer_tid=pthread_getthreadid_np();p.rows.reserve(384);
    p.sampling.store(true);p.observer=std::thread([&p]{p.observe();});
    const auto started=ProfileClock::now();
    while (!p.ready.load(std::memory_order_acquire)) {
        if (profile_elapsed_ns(started)>2000000000ull || usleep(1000))
            throw std::runtime_error("The source diagnostic observer has uncertain startup; owner retained");
    }
}
void SourceContentionMonitor::begin_pair(unsigned round,unsigned mode,unsigned index,
        const std::array<SourceReadRequest,2> & requests,const std::array<std::uint64_t,2> & expected,
        const CompletedSourcePair & key) {
    auto & p=*impl_;
    if (!p.started || p.finished || active() || round>=3 || mode>=4 || index>=32 || p.rows.size()>=384)
        throw std::runtime_error("The native diagnostic exceeds its once-only completed trace");
    p.current={};p.current.round=round;p.current.mode=mode;p.current.index=index;
    p.current.key=key;p.current.requests=requests;p.current.expected=expected;
    p.current.before=observe_native_system_memory();p.phase.store(round*4+mode);
    p.current.begin=clock_ns(CLOCK_MONOTONIC,true);p.pair_active.store(true,std::memory_order_release);
    p.observe_pair.store(round!=2,std::memory_order_release);
}
std::int64_t SourceContentionMonitor::read_at(int fd,void * target,std::size_t bytes,std::uint64_t offset) {
    auto & p=*impl_;const unsigned i=target==p.current.requests[0].target?0:1;
    const auto & expected=p.current.requests[i];auto & r=p.current.reads[i];
    if (!active() || expected.fd!=fd || expected.target!=target || expected.bytes!=bytes || expected.offset!=offset)
        throw std::runtime_error("A source diagnostic read differs from its completed trace");
    rusage a{},b{};const bool have_usage=thread_usage(a);const auto cpu=clock_ns(CLOCK_THREAD_CPUTIME_ID,false);
    r.begin=clock_ns(CLOCK_MONOTONIC,true);errno=0;
    r.got=p.current.mode==0?std::int64_t(p.current.expected[i]):pread(fd,target,bytes,static_cast<off_t>(offset));
    r.error=errno;r.end=clock_ns(CLOCK_MONOTONIC,true);const auto cpu_end=clock_ns(CLOCK_THREAD_CPUTIME_ID,false);
    if (cpu && cpu_end>=cpu) r.cpu=cpu_end-cpu;
    if (have_usage && thread_usage(b)) {r.voluntary=b.ru_nvcsw-a.ru_nvcsw;r.involuntary=b.ru_nivcsw-a.ru_nivcsw;}
    return r.got;
}
void SourceContentionMonitor::complete_pair(const std::array<std::int64_t,2> & got) {
    auto & p=*impl_;p.current.end=clock_ns(CLOCK_MONOTONIC,true);
    p.observe_pair.store(false,std::memory_order_release);p.pair_active.store(false,std::memory_order_release);
    for (unsigned i=0;i<2;++i) if (got[i]<0 || std::uint64_t(got[i])!=p.current.expected[i] ||
        p.current.reads[i].got!=got[i] || !p.current.reads[i].begin || p.current.reads[i].end<p.current.reads[i].begin)
        throw std::runtime_error("A source trace diagnostic did not complete its exact read count");
    if (p.current.mode) {
        std::array<std::uint64_t,2> hashes{};
        for (unsigned i=0;i<2;++i) hashes[i]=page_sample(p.current.requests[i],p.current.expected[i]);
        const auto index=p.current.index;
        if (!p.reference_ready[index]) {p.reference[index]=hashes;p.reference_ready[index]=true;}
        else if (p.reference[index]!=hashes) throw std::runtime_error("Completed source diagnostic page samples differ");
    }
    p.current.after=observe_native_system_memory();p.rows.push_back(p.current);
}
std::string SourceContentionMonitor::finish_completed() {
    auto & p=*impl_;
    if (active() || p.finished || p.rows.size()!=384) throw std::runtime_error("The complete bounded source diagnostic is required");
    p.sampling.store(false,std::memory_order_release);p.observer.join();p.finished=true;
    using Json=nlohmann::json;Json rows=Json::array(),waits=Json::array();
    for (const auto & r:p.rows) {
        const auto & a=r.reads[0];const auto & b=r.reads[1];
        const auto overlap_begin=std::max(a.begin,b.begin),overlap_end=std::min(a.end,b.end);
        Json row={{"round",r.round},{"mode",r.mode},{"index",r.index},{"completed_trace_ordinal",r.key.completed_ordinal},{"files",r.key.files},
            {"logical_offsets",r.key.offsets},{"logical_bytes_each",r.key.bytes},
            {"requested_bytes",{r.requests[0].bytes,r.requests[1].bytes}},
            {"aligned_offsets",{r.requests[0].offset,r.requests[1].offset}},
            {"wall_ns",r.end-r.begin},{"read_wall_ns",{a.end-a.begin,b.end-b.begin}},
            {"thread_CPU_ns",{a.cpu,b.cpu}},{"voluntary_switches",{a.voluntary,b.voluntary}},
            {"involuntary_switches",{a.involuntary,b.involuntary}},
            {"overlap_ns",overlap_end>overlap_begin?overlap_end-overlap_begin:0},
            {"worker_dispatch_ns",r.mode==0||r.mode==2?b.begin-r.begin:0},
            {"after_producer_ns",r.end-a.end},{"after_worker_ns",r.end-b.end},
            {"kernel_free_before",r.before.kernel_free},{"kernel_free_after",r.after.kernel_free},
            {"kernel_minimum",r.before.kernel_minimum},{"kernel_reserved",r.before.kernel_reserved},
            {"Flexible_before",r.before.flexible_available},{"Flexible_after",r.after.flexible_available}};
        rows.push_back(std::move(row));
    }
    for (unsigned i=0;i<p.wait_count;++i) waits.push_back({{"round",p.waits[i].phase/4},
        {"mode",p.waits[i].phase%4},{"name",p.waits[i].name},{"samples",p.waits[i].count}});
    return Json{{"schema","ps5-qwen-completed-source-contention-v1"},{"completed",true},
        {"completed_actual_trace_pairs",32},{"rounds",3},{"modes",4},{"measured_pairs",384},
        {"trace_sampling_interval",512},
        {"source_window_bytes",model_read_window},{"maximum_open_source_handles",8},
        {"production_outstanding_reads",1},{"diagnostic_maximum_outstanding_reads",2},
        {"new_GPU_commands",0},{"additional_source_payload_buffers",0},{"automatic_IO_retries",0},
        {"all_read_counts_exact",true},{"completed_page_samples_match",true},{"full_payload_hashes_compared",false},
        {"source_observer_positively_joined",true},{"sampler_interval_us",1000},{"sampler_queries",p.queries},
        {"sampler_errors",p.query_errors},{"sampler_unmatched_PID_thread",p.unmatched},
        {"last_round_sampling_disabled",true},{"rows",rows},{"wait_channels",waits}}.dump();
}
}
