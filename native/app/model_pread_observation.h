// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <atomic>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
struct ObservedReadIdentity {
    std::array<std::uint64_t,12> fields{};
    std::int64_t flags=-1;
    bool valid=false;
};
struct ObservedReadRow {
    std::uint64_t ordinal=0,begin_ns=0,end_ns=0,thread=0,offset=0,requested=0;
    std::int64_t returned=-1,flags_before=-1,flags_after=-1;
    std::array<std::uint64_t,12> before{},after{};
    std::int32_t descriptor=-1,error=0;
    std::uint32_t before_valid=0,after_valid=0,identity_equal=0,candidate=0;
};
static_assert(sizeof(ObservedReadRow)==288,"Fixed diagnostic row ABI");
struct ObservedReadHooks {
    std::int64_t(*read)(int,void*,std::size_t,std::int64_t)=nullptr;
    ObservedReadIdentity(*inspect)(int)noexcept=nullptr;
    std::uint64_t(*clock)()noexcept=nullptr;
    std::uint64_t(*thread)()noexcept=nullptr;
};

// Observe one original request, including calls from its original source
// workers. This class never predicts, changes arguments, reads payload bytes,
// opens a source descriptor, retries I/O or creates a worker/GPU operation.
template<std::size_t Capacity=32768>class ModelPreadObservation {
    ObservedReadHooks hooks_;
    std::array<ObservedReadRow,Capacity>rows_{};
    std::atomic<std::uint64_t>count_{0},candidates_{0},active_{0},forwarded_{0};
    std::atomic<bool>enabled_{false};
    bool attempted_=false,stopped_=false;
public:
    explicit ModelPreadObservation(ObservedReadHooks hooks):hooks_(hooks){
        if(!hooks.read||!hooks.inspect||!hooks.clock||!hooks.thread)throw std::invalid_argument("Complete read-only observation hooks required");
    }
    void begin(){
        if(attempted_||active_.load())throw std::logic_error("One bounded source observation request required");
        attempted_=true;enabled_.store(true,std::memory_order_release);
    }
    std::int64_t read(int fd,void*to,std::size_t bytes,std::int64_t offset){
        const int incoming=errno;
        if(!enabled_.load(std::memory_order_acquire))return hooks_.read(fd,to,bytes,offset);
        active_.fetch_add(1,std::memory_order_acq_rel);
        if(!enabled_.load(std::memory_order_acquire)){
            active_.fetch_sub(1,std::memory_order_release);errno=incoming;return hooks_.read(fd,to,bytes,offset);
        }
        // Preserve every call's sequence, including unsupported reads which
        // reset a predictor. Only large aligned reads add descriptor observations.
        const bool candidate=bytes>=(256u<<10)&&bytes<=(8u<<20)&&!(bytes%16384)&&offset>=0&&!(offset%16384);
        const auto ordinal=count_.fetch_add(1,std::memory_order_relaxed);
        if(candidate)candidates_.fetch_add(1,std::memory_order_relaxed);
        ObservedReadRow*row=ordinal<Capacity?&rows_[ordinal]:nullptr;
        if(row){
            row->ordinal=ordinal;row->descriptor=fd;row->offset=std::uint64_t(offset);row->requested=bytes;
            row->candidate=candidate;
            if(candidate){const auto identity=hooks_.inspect(fd);row->before=identity.fields;row->flags_before=identity.flags;row->before_valid=identity.valid;}
            row->thread=hooks_.thread();row->begin_ns=hooks_.clock();
        }
        errno=incoming;
        const auto result=hooks_.read(fd,to,bytes,offset);const int returned_error=errno;
        forwarded_.fetch_add(1,std::memory_order_relaxed);
        if(row){
            row->end_ns=hooks_.clock();row->returned=result;row->error=returned_error;
            if(candidate){const auto identity=hooks_.inspect(fd);row->after=identity.fields;row->flags_after=identity.flags;row->after_valid=identity.valid;}
            row->identity_equal=row->before_valid&&row->after_valid&&row->before==row->after&&row->flags_before==row->flags_after;
        }
        active_.fetch_sub(1,std::memory_order_release);errno=returned_error;return result;
    }
    void stop_after_original_source_completion(){
        enabled_.store(false,std::memory_order_release);
        if(!attempted_||stopped_||active_.load(std::memory_order_acquire))
            throw std::runtime_error("Original source reads must complete before diagnostic retirement; retain owner");
        stopped_=true;
    }
    bool stopped()const noexcept{return stopped_;}
    std::uint64_t calls()const noexcept{return count_.load();}
    std::uint64_t candidates()const noexcept{return candidates_.load();}
    std::uint64_t forwarded()const noexcept{return forwarded_.load();}
    std::size_t retained()const noexcept{return std::size_t(calls()<Capacity?calls():Capacity);}
    const ObservedReadRow*rows()const{
        if(!stopped_)throw std::logic_error("Only completed source records may be exported");return rows_.data();
    }
};
}
