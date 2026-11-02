// SPDX-License-Identifier: MIT
#include "model_pread_observation.h"
#include <cassert>
#include <thread>
#include <vector>
namespace {
std::atomic<unsigned>calls{0},generation{0};
std::atomic<std::uint64_t>clock_value{1};
std::int64_t read(int fd,void*to,std::size_t bytes,std::int64_t offset){
    assert(to&&offset>=0&&errno==E2BIG);++calls;
    if(fd<0){errno=EINTR;return -1;}
    *static_cast<unsigned char*>(to)=0x5a;
    if(fd==7)++generation;
    errno=fd==3?ENOSPC:EBUSY;return fd==3?std::int64_t(bytes/2):std::int64_t(bytes);
}
qwen_app::ObservedReadIdentity inspect(int fd)noexcept{
    qwen_app::ObservedReadIdentity identity;identity.fields[0]=generation;identity.fields[1]=std::uint64_t(fd);
    identity.valid=fd>=0;identity.flags=fd;errno=EINVAL;return identity;
}
std::uint64_t clock()noexcept{errno=EACCES;return clock_value++;}
std::uint64_t thread()noexcept{return std::hash<std::thread::id>{}(std::this_thread::get_id());}
}
int main(){
    constexpr std::size_t bytes=256u<<10;unsigned char data[8]{};
    qwen_app::ModelPreadObservation<4>trace({read,inspect,clock,thread});
    errno=E2BIG;assert(trace.read(1,data,bytes,0)==std::int64_t(bytes)&&errno==EBUSY&&calls==1);
    trace.begin();
    for(int fd:{1,3,7,-1,2}){
        errno=E2BIG;const auto got=trace.read(fd,data,bytes,16384);
        assert(got==(fd<0?-1:fd==3?std::int64_t(bytes/2):std::int64_t(bytes)));
        assert(errno==(fd<0?EINTR:fd==3?ENOSPC:EBUSY));
    }
    errno=E2BIG;assert(trace.read(1,data,16,0)==16&&errno==EBUSY);
    trace.stop_after_original_source_completion();
    assert(trace.forwarded()==6&&trace.calls()==6&&trace.candidates()==5&&trace.retained()==4&&calls==7);
    const auto*rows=trace.rows();assert(rows[0].identity_equal&&rows[0].returned==std::int64_t(bytes));
    assert(rows[1].returned==std::int64_t(bytes/2)&&rows[1].error==ENOSPC);
    assert(!rows[2].identity_equal&&rows[2].before[0]!=rows[2].after[0]);
    assert(!rows[3].before_valid&&!rows[3].after_valid&&rows[3].returned==-1&&rows[3].error==EINTR);
    bool refused=false;try{trace.begin();}catch(const std::logic_error&){refused=true;}assert(refused);
    qwen_app::ModelPreadObservation<256>parallel({read,inspect,clock,thread});parallel.begin();
    std::vector<std::thread>workers;
    for(unsigned i=0;i<4;++i)workers.emplace_back([&]{unsigned char destination[8]{};
        for(unsigned n=0;n<50;++n){errno=E2BIG;assert(parallel.read(1,destination,bytes,n*16384)==std::int64_t(bytes));assert(errno==EBUSY&&destination[0]==0x5a);}});
    for(auto&worker:workers)worker.join();parallel.stop_after_original_source_completion();
    assert(parallel.candidates()==200&&parallel.forwarded()==200&&calls==207);
    rows=parallel.rows();for(unsigned i=0;i<200;++i)assert(rows[i].ordinal==i&&rows[i].identity_equal&&rows[i].end_ns>rows[i].begin_ns);
}
