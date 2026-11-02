// SPDX-License-Identifier: MIT
#include "immutable_span_fixture.h"
#include "immutable_span_prefetch.h"
#include "immutable_span_assets.h"
#include "system_memory.h"
#include <ps5platform/heap.h>
#include <array>
#include <chrono>
#include <cerrno>
#include <cstdlib>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

namespace qwen_app {
namespace {
using Clock=std::chrono::steady_clock;
using Json=nlohmann::json;
void need(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
bool describe(int fd,ImmutableSpanIdentity&identity,Json*diagnostic){
    struct stat s{};errno=0;const int flags=fcntl(fd,F_GETFL),flag_error=errno;
    errno=0;const int rc=fstat(fd,&s),stat_error=errno;
    if(diagnostic)*diagnostic={{"flags",flags},{"flags_errno",flag_error},{"fstat_rc",rc},{"stat_errno",stat_error},
        {"device",s.st_dev},{"inode",s.st_ino},{"mode",s.st_mode},{"uid",s.st_uid},{"gid",s.st_gid},
        {"bytes",s.st_size},{"links",s.st_nlink},{"stat_flags",s.st_flags}};
    if(flags<0||(flags&O_ACCMODE)!=O_RDONLY||!(flags&O_DIRECT)||rc||!S_ISREG(s.st_mode)||
       !s.st_ino||s.st_size<=0||(s.st_mode&0022)||s.st_nlink>1)return false;
    identity={std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_size),std::uint64_t(s.st_mode),
        std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_nlink),std::uint64_t(s.st_flags),
        s.st_mtim.tv_sec,s.st_mtim.tv_nsec,s.st_ctim.tv_sec,s.st_ctim.tv_nsec};return true;
}
bool inspect(int fd,ImmutableSpanIdentity&identity){return describe(fd,identity,nullptr);}
void*allocation(std::size_t n){
    (void)admit_native_system_memory();void*p=nullptr;
    need(!posix_memalign(&p,16384,n)&&p&&ps5_heap_owns(p),"Tracked aligned span fixture allocation required");return p;
}
Json stats(const ImmutableSpanStats&s){return {{"foreground_calls",s.foreground_calls},{"foreground_bytes",s.foreground_bytes},
    {"prefetch_calls",s.prefetch_calls},{"prefetch_bytes",s.prefetch_bytes},{"hits",s.hits},{"hit_bytes",s.hit_bytes},
    {"unused",s.unused},{"declined",s.declined},{"invalid",s.invalid},{"waits",s.waits},
    {"admission_declines",s.admission_declines},{"descriptor_declines",s.descriptor_declines}};}
struct State {
    int source=-1;ImmutableSpanIdentity original{};
    std::shared_ptr<void> scratch,destination,reference;
    ImmutableSpanPrefetch*reader=nullptr;
    int opening_descriptor=-1,last_lease_open_errno=0;
    std::uint64_t lease_opens=0,lease_closes=0;
    void(*stage)(const char*)=nullptr;
};
}
Json run_immutable_span_fixture(void(*stage)(const char*),std::uint64_t admitted_SELF_bytes){
    need(stage,"Durable stage callback required");
    // Keep the complete allocation/worker/source graph alive after uncertainty.
    auto*s=new State;s->stage=stage;
    stage("I1_fixture_before_readonly_source_open");
    errno=0;s->source=open(span_source_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);const int open_error=errno;
    Json initial={{"open_succeeded",s->source>=0},{"open_errno",open_error},{"source_namespace",span_source_namespace}};
    Json metadata;const bool descriptor_ok=s->source>=0&&describe(s->source,s->original,&metadata);initial["descriptor"]=metadata;
    struct stat title_directory{},title_SELF{};errno=0;
    const int directory_rc=stat("/app0/.",&title_directory),directory_error=errno;
    errno=0;const int SELF_rc=lstat("/app0/eboot.bin",&title_SELF),SELF_error=errno;
    initial["title_directory"]={{"stat_rc",directory_rc},{"errno",directory_error},{"device",title_directory.st_dev},
        {"inode",title_directory.st_ino},{"mode",title_directory.st_mode}};
    initial["title_SELF_diagnostic_only"]={{"lstat_rc",SELF_rc},{"errno",SELF_error},{"device",title_SELF.st_dev},
        {"inode",title_SELF.st_ino},{"mode",title_SELF.st_mode},{"bytes",title_SELF.st_size},{"admitted_deployed_SELF_bytes",admitted_SELF_bytes}};
    const auto&i=s->original;
    const bool namespace_ok=!directory_rc&&S_ISDIR(title_directory.st_mode)&&title_directory.st_ino&&
        i.device==std::uint64_t(title_directory.st_dev);
    const bool identity_ok=i.inode==span_source_identity[1]&&
        i.mode==span_source_identity[2]&&i.uid==span_source_identity[3]&&i.gid==span_source_identity[4]&&
        i.bytes==span_source_identity[5]&&i.modified_seconds==std::int64_t(span_source_identity[6])&&
        i.modified_ns==std::int64_t(span_source_identity[7])&&i.changed_seconds==std::int64_t(span_source_identity[8])&&
        i.changed_ns==std::int64_t(span_source_identity[9]);
    const bool admitted=descriptor_ok&&namespace_ok&&identity_ok;
    initial.update({{"same_title_directory_device",namespace_ok},{"original_nondevice_identity_equal",identity_ok}});
    stage("I1_fixture_source_open_and_metadata_returned");
    if(!admitted||span_descriptor_only){
        if(s->source>=0)need(close(s->source)==0,"Returned CPU source refusal descriptor close failed; retain owner");
        delete s;
        return {{"schema","ps5-qwen-immutable-byte-span-fixture-v1"},{"completed",true},{"all_bytes_and_canaries_passed",false},
            {"cases",Json::array()},{"source_open_and_metadata",initial},{"known_returned_source_admission_refusal",!admitted},
            {"descriptor_only",span_descriptor_only},{"descriptor_admission_passed",admitted},
            {"source_descriptor_worker_and_scratch_retired",true},{"model_loads",0},{"GPU_calls",0},{"payload_writes",0},
            {"additional_worker_created",false},{"model_speed_qualified",false}};
    }
    constexpr std::size_t capacity=1u<<20,guard=16384;
    s->scratch=std::shared_ptr<void>(allocation(capacity),free);
    s->destination=std::shared_ptr<void>(allocation(capacity+2*guard),free);
    s->reference=std::shared_ptr<void>(allocation(capacity),free);
    ImmutableSpanHooks hooks;
    hooks.inspect=inspect;
    hooks.duplicate=[s](int fd){
        ImmutableSpanIdentity original{},separate{};
        if(!inspect(fd,original)||!(original==s->original))return -1;
        errno=0;s->opening_descriptor=open(span_source_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);s->last_lease_open_errno=errno;
        if(s->opening_descriptor<0)return -1;
        ++s->lease_opens;
        if(!inspect(s->opening_descriptor,separate)||!(separate==original)){
            need(close(s->opening_descriptor)==0,"Independent source descriptor refusal close failed; retain owner");
            ++s->lease_closes;s->opening_descriptor=-1;return -1;
        }
        const int acquired=s->opening_descriptor;s->opening_descriptor=-1;return acquired;
    };
    hooks.close=[s](int fd){if(close(fd))return false;++s->lease_closes;return true;};
    hooks.read=[](int fd,void*p,std::size_t n,std::uint64_t offset)->std::ptrdiff_t{
        // Observation is thread-local and read-only; never use the mutable
        // frontend admission/wait state from the background producer.
        (void)qualified_system_headroom(observe_native_system_memory());
        return pread(fd,p,n,off_t(offset));
    };
    hooks.admit=[](std::size_t){try{(void)admit_native_system_memory();return true;}catch(const KernelMemoryPressure&){return false;}};
    hooks.stage=stage;s->reader=new ImmutableSpanPrefetch(std::move(hooks),s->scratch.get(),capacity,s->scratch);
    Json cases=Json::array();bool all=true;
    const auto end=Clock::now()+std::chrono::seconds(120);
    for(const std::size_t bytes:{540672u,557056u,475136u,491520u})for(unsigned enabled=0;enabled<2;++enabled){
        const auto before=s->reader->snapshot();s->reader->begin_request(enabled!=0);
        bool equal=true,canaries=true,returned=true;std::uint64_t independent_reads=0,independent_bytes=0;
        std::array<double,8>read_us{};
        for(unsigned ordinal=0;ordinal<8;++ordinal){
            need(Clock::now()<end,"Finite span fixture deadline reached; retain owner");
            auto*buffer=static_cast<unsigned char*>(s->destination.get());std::memset(buffer,0xA5,capacity+2*guard);
            const std::uint64_t offset=(16ull<<20)+ordinal*bytes;
            stage("I1_fixture_before_foreground_span_read");const auto start=Clock::now();
            const auto got=s->reader->read(s->source,buffer+guard,bytes,offset);
            read_us[ordinal]=std::chrono::duration<double,std::micro>(Clock::now()-start).count();
            stage("I1_fixture_foreground_span_read_returned");
            if(got!=std::ptrdiff_t(bytes)){returned=false;break;}
            (void)admit_native_system_memory();stage("I1_fixture_before_independent_Direct_reference_read");
            const auto reference=pread(s->source,s->reference.get(),bytes,off_t(offset));
            stage("I1_fixture_independent_Direct_reference_read_returned");++independent_reads;
            if(reference>0)independent_bytes+=std::uint64_t(reference);
            if(reference!=ssize_t(bytes)){returned=false;break;}
            equal=equal&&!std::memcmp(buffer+guard,s->reference.get(),bytes);
            for(std::size_t k=0;k<guard;++k)canaries=canaries&&buffer[k]==0xA5&&buffer[guard+bytes+k]==0xA5;
            ImmutableSpanIdentity current{};need(inspect(s->source,current)&&current==s->original,"Fixture source changed during delivery");
        }
        stage("I1_fixture_before_request_worker_drain");s->reader->finish_request();stage("I1_fixture_request_worker_drain_completed");
        const auto after=s->reader->snapshot();auto delta=after;
#define DELTA(member) delta.member-=before.member
        DELTA(foreground_calls);DELTA(foreground_bytes);DELTA(prefetch_calls);DELTA(prefetch_bytes);DELTA(hits);DELTA(hit_bytes);
        DELTA(unused);DELTA(declined);DELTA(invalid);DELTA(waits);
        DELTA(admission_declines);DELTA(descriptor_declines);
#undef DELTA
        const bool passed=returned&&equal&&canaries&&delta.invalid==0&&
            (enabled?(delta.hits+delta.foreground_calls==8):(delta.hits==0&&delta.foreground_calls==8));
        cases.push_back({{"span_bytes",bytes},{"prefetch_enabled",enabled!=0},{"read_calls_returned",returned},
            {"all_bytes_equal_independent_Direct_reads",equal},{"canaries_equal",canaries},{"passed",passed},
            {"source_calls",stats(delta)},{"foreground_read_wall_us",read_us},
            {"independent_reference_reads",independent_reads},{"independent_reference_bytes",independent_bytes}});
        all=all&&passed;if(!returned)break;
    }
    stage("I1_fixture_before_worker_close");s->reader->close_completed();delete s->reader;s->reader=nullptr;
    stage("I1_fixture_worker_join_and_scratch_lease_completed");
    ImmutableSpanIdentity final{};need(inspect(s->source,final)&&final==s->original,"Final span source identity changed");
    const bool zero_title_links=final.links==0;
    need(s->opening_descriptor<0&&s->lease_opens==s->lease_closes,"All independent immutable source leases must retire");
    const auto lease_opens=s->lease_opens,lease_closes=s->lease_closes;const int lease_errno=s->last_lease_open_errno;
    need(close(s->source)==0,"Span fixture source close failed; retain owner");s->source=-1;
    s->scratch.reset();s->destination.reset();s->reference.reset();delete s;
    return {{"schema","ps5-qwen-immutable-byte-span-fixture-v1"},{"completed",true},{"all_bytes_and_canaries_passed",all},
        {"source_open_and_metadata",initial},{"source_device_equals_same_launch_title_directory",true},
        {"native_title_device",title_directory.st_dev},{"zero_title_link_count_preserved",zero_title_links},
        {"source_lease_method","Separate read-only open with exact full descriptor identity"},
        {"source_lease_opens",lease_opens},{"source_lease_closes",lease_closes},{"last_lease_open_errno",lease_errno},
        {"cases",cases},{"prior_whole_source_SHA256",span_source_sha256},{"fresh_whole_source_hash_claimed",false},
        {"fresh_full_descriptor_identity_preserved",true},{"source_descriptor_worker_and_scratch_retired",true},
        {"model_loads",0},{"GPU_calls",0},{"payload_writes",0},{"maximum_predictions_per_request",6},
        {"timings_include_prediction_and_wait",true},{"independent_reference_IO_between_reads",true},
        {"model_demand_trace_replayed",false},{"model_speed_qualified",false}};
}
}
