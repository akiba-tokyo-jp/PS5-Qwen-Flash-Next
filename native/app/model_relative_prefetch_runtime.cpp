// SPDX-License-Identifier: MIT
#include "model_relative_prefetch.h"
#include "model_relative_prefetch_runtime.h"
// Keep this stricter read-only helper separate from the selected frontend's
// phase-aware inline function; never contribute a conflicting definition.
#define qualified_system_headroom relative_prefetch_qualified_system_headroom
#include "system_memory.h"
#undef qualified_system_headroom
#include <fcntl.h>
#include <ps5platform/heap.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
extern "C" {
ssize_t __real_pread(int,void*,std::size_t,off_t);
int __real_close(int);
void qwen_native_halt(const char*) __attribute__((noreturn));
}
static_assert(sizeof(off_t)==8,"The original native pread ABI requires64-bit offsets");
namespace {
qwen_app::ModelRelativePrefetch*owner=nullptr;
bool prepared=false,selected=false;
unsigned requests=0;
qwen_app::RelativePrefetchStats last;
std::uint64_t now(){
    timespec t{};
    if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000)
        throw std::runtime_error("A valid native completion clock is required");
    return std::uint64_t(t.tv_sec)*1000000000ull+std::uint64_t(t.tv_nsec);
}
qwen_app::ObservedReadIdentity inspect(int fd){
    qwen_app::ObservedReadIdentity out;struct stat s{};
    out.flags=fcntl(fd,F_GETFL);const int rc=fstat(fd,&s);
    if(!rc)out.fields={std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_size),
        std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_nlink),
        std::uint64_t(s.st_flags),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),
        std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};
    out.valid=!rc&&out.flags>=0&&(out.flags&O_ACCMODE)==O_RDONLY&&(out.flags&O_DIRECT)&&
        S_ISREG(s.st_mode)&&s.st_ino&&s.st_size>0&&!(s.st_mode&0022)&&s.st_nlink<=1;
    return out;
}
nlohmann::json statistics(const qwen_app::RelativePrefetchStats&s){
    return {{"original_reads",s.original_reads},{"original_bytes",s.original_bytes},{"predictions",s.predictions},
        {"predicted_bytes",s.predicted_bytes},{"hits",s.hits},{"hit_bytes",s.hit_bytes},{"unused",s.unused},
        {"invalid",s.invalid},{"declines",s.declines},{"maximum_simultaneous_reads",s.maximum_simultaneous_reads},
        {"worker_creations",s.worker_creations},{"positive_worker_reads",s.positive_worker_reads},
        {"speculative_reads",s.speculative_reads},{"speculative_returned_calls",s.speculative_returned_calls},
        {"speculative_bytes",s.speculative_bytes},{"completed_worker_jobs",s.completed_worker_jobs}};
}
}
extern "C" ssize_t __wrap_pread(int fd,void*destination,std::size_t bytes,off_t offset){
    if(!owner)return __real_pread(fd,destination,bytes,offset);
    try{return ssize_t(owner->read(fd,destination,bytes,std::int64_t(offset)));}
    catch(...){qwen_native_halt("relative_model_read_uncertain_all_source_and_backing_retained");}
}
extern "C" int __wrap_close(int fd){
    if(!owner)return __real_close(fd);
    try{return owner->close_source(fd);}
    catch(...){qwen_native_halt("relative_model_source_close_uncertain_original_fd_retained");}
}
namespace qwen_app {
void prepare_model_relative_prefetch(bool enabled,bool(*admit)(std::size_t),std::uint64_t heap_limit,std::uint64_t reserve){
    if(prepared||owner||!admit||!heap_limit||!reserve)throw std::runtime_error("One original prefetch preparation required");
    prepared=true;selected=enabled;if(!enabled)return;
    constexpr std::size_t capacity=2u<<20;
    if(!admit(capacity))throw std::runtime_error("Original physical/CPU admission refuses speculative scratch");
    void*allocation=ps5_heap_memalign(16384,capacity);
    if(!allocation||!ps5_heap_owns(allocation))throw std::runtime_error("Actual tracked CPU Direct scratch required; no libc fallback");
    const auto scratch=std::shared_ptr<void>(allocation,ps5_heap_free);
    RelativePrefetchHooks hooks;
    hooks.read=[](int fd,void*p,std::size_t bytes,std::int64_t offset){return std::int64_t(__real_pread(fd,p,bytes,off_t(offset)));};
    hooks.inspect=inspect;hooks.close=[](int fd){return __real_close(fd);};
    // Original source producers and the extra worker must not mutate the
    // frontend's admission/wait state. Use fresh read-only observations.
    hooks.admit=[heap_limit,reserve](std::size_t){try{
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        return !heap.libc_fallbacks&&heap.mapped_bytes<=heap_limit&&heap.peak_bytes<=heap_limit&&
            relative_prefetch_qualified_system_headroom(observe_native_system_memory())>=reserve;
        }catch(...){return false;}};
    owner=new ModelRelativePrefetch(std::move(hooks),allocation,capacity,scratch);
    if(!ps5_heap_owns(owner))qwen_native_halt("relative_model_owner_allocation_not_tracked_backing_retained");
}
void begin_model_relative_prefetch_request(){
    if(!prepared||requests>=3||(selected&&!owner))throw std::runtime_error("One of the three original source requests is required");
    if(owner)owner->begin_request();++requests;
}
nlohmann::json finish_model_relative_prefetch_request(){
    if(!prepared||!requests)throw std::runtime_error("A prepared original request must complete first");
    const auto begin=now();if(owner)last=owner->finish_request();const auto end=now();
    if(end<begin)throw std::runtime_error("Prefetch completion clock regressed");
    return {{"completed",true},{"enabled",selected},{"ordinal",requests-1},{"cumulative",statistics(last)},
        {"final_source_drain_ns",end-begin},{"additional_source_FDs",0},{"scratch_bytes",selected?2u<<20:0},
        {"all_original_and_speculative_IO_returned",true},{"GPU_calls_added",0}};
}
nlohmann::json retire_model_relative_prefetch_after_original_owners(){
    if(!prepared||requests!=3)throw std::runtime_error("All three original requests must positively complete");
    const auto started=now();if(owner){last=owner->close_completed();delete owner;owner=nullptr;}
    const auto ended=now();if(ended<started)throw std::runtime_error("Prefetch retirement clock regressed");
    if(last.predictions!=last.hits+last.unused||last.completed_worker_jobs!=last.predictions||
       last.speculative_reads!=last.speculative_returned_calls||last.maximum_simultaneous_reads>4||last.worker_creations>1)
        throw std::runtime_error("Every speculative job, actual source read and original limit must reconcile");
    return {{"completed",true},{"enabled",selected},{"requests",requests},{"cumulative",statistics(last)},
        {"worker_joined_and_actual_scratch_lease_retired",true},{"original_source_FDs_held_until_same_pending_read_returned",true},
        {"additional_source_FDs",0},{"maximum_pending_spans",1},{"all_original_native_guards_unchanged",true},
        {"final_worker_and_scratch_retirement_ns",ended-started},
        {"GPU_calls_added",0},{"broader_prediction_quality_qualified",false},{"model_decode_speed_qualified",false}};
}
}
