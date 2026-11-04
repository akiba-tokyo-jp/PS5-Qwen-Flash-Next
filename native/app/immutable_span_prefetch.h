// SPDX-License-Identifier: MIT
#pragma once
#include "expert_prefetch_io.h"
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>

namespace qwen_app {
struct ImmutableSpanIdentity {
    // Full descriptor identity, never a descriptor number or pathname alone.
    std::uint64_t device=0,inode=0,bytes=0,mode=0,uid=0,gid=0,links=0,flags=0;
    std::int64_t modified_seconds=0,modified_ns=0,changed_seconds=0,changed_ns=0;
    bool operator==(const ImmutableSpanIdentity&o)const noexcept {
        return device==o.device&&inode==o.inode&&bytes==o.bytes&&mode==o.mode&&uid==o.uid&&gid==o.gid&&
            links==o.links&&flags==o.flags&&modified_seconds==o.modified_seconds&&modified_ns==o.modified_ns&&
            changed_seconds==o.changed_seconds&&changed_ns==o.changed_ns;
    }
};
struct ImmutableSpanHooks {
    // inspect also enforces a read-only regular O_DIRECT source and immutable
    // permissions. The caller retains its original source and destination gates.
    std::function<bool(int,ImmutableSpanIdentity&)> inspect;
    // Obtain a separately owned descriptor to the same immutable source.
    // This may reopen and compare full identity when descriptor duplication
    // is unavailable in the title sandbox.
    std::function<int(int)> duplicate;
    std::function<std::ptrdiff_t(int,void*,std::size_t,std::uint64_t)> read;
    std::function<bool(int)> close;
    std::function<bool(std::size_t)> admit;
    std::function<void(const char*)> stage;
};
struct ImmutableSpanStats {
    std::uint64_t foreground_calls=0,foreground_bytes=0,prefetch_calls=0,prefetch_bytes=0;
    std::uint64_t hits=0,hit_bytes=0,unused=0,declined=0,invalid=0,waits=0;
    std::uint64_t admission_declines=0,descriptor_declines=0;
};

// A bounded byte-span predictor. It has no BF16, Expert count, cache-plane or
// model geometry assumption. One admitted producer uses one CPU-only worker.
// Unknown completion retains the worker, duplicated descriptor and allocation.
class ImmutableSpanPrefetch {
    struct State {
        ImmutableSpanHooks hooks;
        void*scratch;
        std::size_t capacity;
        std::shared_ptr<void> allocation;
        ExpertPrefetchIO worker;
        ImmutableSpanStats stats;
        ImmutableSpanIdentity previous{},predicted{};
        std::uint64_t previous_offset=0,predicted_offset=0;
        std::size_t previous_bytes=0,predicted_bytes=0;
        unsigned maximum=0,submitted=0;
        int descriptor=-1;
        const std::thread::id producer=std::this_thread::get_id();
        bool active=false,enabled=false,have_previous=false,pending=false,valid=false,close_returned=true,unknown=false,descriptor_refused=false;
        State(ImmutableSpanHooks h,void*p,std::size_t n,std::shared_ptr<void>lease):
            hooks(std::move(h)),scratch(p),capacity(n),allocation(std::move(lease)){}
    };
    State*state_=nullptr;
    State&state()const {
        if(!state_||state_->producer!=std::this_thread::get_id())
            throw std::runtime_error("One original live prefetch producer required");
        return *state_;
    }
    static bool geometry(const State&s,const ImmutableSpanIdentity&i,std::size_t n,std::uint64_t off)noexcept {
        constexpr std::uint64_t alignment=16384;
        return i.inode&&i.bytes>=(64ull<<20)&&n>=(256u<<10)&&n<=s.capacity&&n<=(8u<<20)&&
            !(n%alignment)&&!(off%alignment)&&off<=i.bytes&&n<=i.bytes-off;
    }
    static void complete(State&s) {
        if(!s.pending)return;
        ++s.stats.waits;
        try{s.worker.complete();}catch(...){s.unknown=true;throw;}
        if(!s.close_returned){s.unknown=true;throw std::runtime_error("Prefetch descriptor retirement unknown; retain owner");}
    }
    static void discard(State&s) {
        if(!s.pending)return;
        complete(s);++s.stats.unused;s.pending=false;s.valid=false;
    }
public:
    ImmutableSpanPrefetch(ImmutableSpanHooks hooks,void*scratch,std::size_t bytes,std::shared_ptr<void>allocation) {
        if(!scratch||!allocation||bytes<(256u<<10)||bytes>(8u<<20)||bytes%16384||
           reinterpret_cast<std::uintptr_t>(scratch)%16384||!hooks.inspect||!hooks.duplicate||!hooks.read||
           !hooks.close||!hooks.admit||!hooks.stage)throw std::invalid_argument("Exact aligned owned prefetch scratch and hooks required");
        state_=new State(std::move(hooks),scratch,bytes,std::move(allocation));
    }
    ImmutableSpanPrefetch(const ImmutableSpanPrefetch&)=delete;
    ImmutableSpanPrefetch&operator=(const ImmutableSpanPrefetch&)=delete;
    // Explicit positive close is required. An exceptional owner never releases
    // resources through an implicit destructor after an opaque read timeout.
    ~ImmutableSpanPrefetch()=default;
    void begin_request(bool enabled,unsigned maximum_predictions=6) {
        auto&s=state();
        if(s.unknown||s.active||s.pending||maximum_predictions>6)throw std::runtime_error("Completed bounded prefetch request required");
        s.active=true;s.enabled=enabled;s.maximum=maximum_predictions;s.submitted=0;s.have_previous=false;s.descriptor_refused=false;
    }
    std::ptrdiff_t read(int fd,void*destination,std::size_t bytes,std::uint64_t offset) {
        auto&s=state();
        if(s.unknown||!s.active)throw std::runtime_error("Active positively completed prefetch owner required");
        ImmutableSpanIdentity before{};const bool supported=s.enabled&&destination&&
            s.hooks.inspect(fd,before)&&geometry(s,before,bytes,offset);
        bool hit=false;
        if(s.pending){
            if(supported&&before==s.predicted&&bytes==s.predicted_bytes&&offset==s.predicted_offset){
                complete(s);ImmutableSpanIdentity after{};
                if(s.valid&&s.hooks.inspect(fd,after)&&after==before){
                    std::memcpy(destination,s.scratch,bytes);hit=true;++s.stats.hits;s.stats.hit_bytes+=bytes;
                }else ++s.stats.invalid;
                s.pending=false;s.valid=false;
            }else discard(s);
        }
        std::ptrdiff_t result=std::ptrdiff_t(bytes);
        if(!hit){
            ++s.stats.foreground_calls;result=s.hooks.read(fd,destination,bytes,offset);
            if(result>0)s.stats.foreground_bytes+=std::uint64_t(result);
        }
        ImmutableSpanIdentity after{};
        if(!supported||result!=std::ptrdiff_t(bytes)||!s.hooks.inspect(fd,after)||!(before==after)){
            s.have_previous=false;return result;
        }
        if(s.have_previous&&s.previous==before&&s.previous_bytes==bytes&&offset>s.previous_offset&&s.submitted<s.maximum&&!s.descriptor_refused){
            const auto stride=offset-s.previous_offset;
            if(stride<=std::numeric_limits<std::uint64_t>::max()-offset&&geometry(s,before,bytes,offset+stride)){
                if(!s.hooks.admit(bytes)){++s.stats.declined;++s.stats.admission_declines;}
                else {
                    s.hooks.stage("immutable_span_prefetch_before_descriptor_duplicate");
                    const int copy=s.hooks.duplicate(fd);
                    if(copy<0){++s.stats.declined;++s.stats.descriptor_declines;s.descriptor_refused=true;}
                    else {
                        s.descriptor=copy;s.predicted=before;s.predicted_bytes=bytes;s.predicted_offset=offset+stride;
                        s.valid=false;s.close_returned=false;s.pending=true;
                        // The pre-operation journal returns before submission.
                        s.hooks.stage("immutable_span_prefetch_before_worker_submit");
                        try{s.worker.submit([&s]{
                            ImmutableSpanIdentity first{},last{};
                            try {
                                if(s.hooks.inspect(s.descriptor,first)&&first==s.predicted){
                                    ++s.stats.prefetch_calls;
                                    const auto got=s.hooks.read(s.descriptor,s.scratch,s.predicted_bytes,s.predicted_offset);
                                    if(got>0)s.stats.prefetch_bytes+=std::uint64_t(got);
                                    s.valid=got==std::ptrdiff_t(s.predicted_bytes)&&s.hooks.inspect(s.descriptor,last)&&last==first;
                                }
                            }catch(...){s.valid=false;}
                            try{s.close_returned=s.hooks.close(s.descriptor);}catch(...){s.close_returned=false;}
                            if(s.close_returned)s.descriptor=-1;
                        });}catch(...){s.unknown=true;throw;}
                        ++s.submitted;
                    }
                }
            }
        }
        s.previous=before;s.previous_bytes=bytes;s.previous_offset=offset;s.have_previous=true;
        return result;
    }
    void finish_request(){auto&s=state();discard(s);s.active=false;s.enabled=false;s.have_previous=false;}
    ImmutableSpanStats snapshot(){auto&s=state();complete(s);return s.stats;}
    void close_completed(){
        if(!state_)return;auto*s=&state();finish_request();s->worker.close_completed();delete s;state_=nullptr;
    }
};
}
