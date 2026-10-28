// SPDX-License-Identifier: MIT
#include "paired_source_io.h"
#include <atomic>
#include <cstdlib>
#include <iostream>
using namespace qwen_app;
struct Ops final:SourceReadOps {
    std::mutex mutex;std::condition_variable changed;
    std::atomic<unsigned> active{0},peak{0},calls{0};bool third=false,force=true,short_read=false;
    SourceIdentity identity(int)override{return {};}
    int open_direct(const std::string &)override{return 1;}
    bool close_file(int)override{return true;}
    std::uint64_t system_headroom()override{return 1ull<<30;}
    std::int64_t read_at(int,void *target,std::size_t bytes,std::uint64_t offset)override{
        ++calls;const auto now=++active;auto old=peak.load();while(old<now&&!peak.compare_exchange_weak(old,now)){}
        if(force&&offset==0){std::unique_lock<std::mutex> lock(mutex);
            if(!changed.wait_for(lock,std::chrono::seconds(2),[&]{return third;}))throw std::runtime_error("Refill barrier remained");}
        if(offset==2*16384){std::lock_guard<std::mutex> lock(mutex);third=true;changed.notify_all();}
        std::memset(target,int(offset/16384+1),bytes);--active;
        return std::int64_t(bytes)-(short_read&&offset==16384?1:0);
    }
};
int main(){
    std::vector<unsigned char> memory(7*16384);const auto base=(reinterpret_cast<std::uintptr_t>(memory.data())+16383)&~std::uintptr_t(16383);
    std::array<SourceReadRequest,6> requests{};
    for(unsigned i=0;i<6;++i)requests[i]={1,reinterpret_cast<void *>(base+i*16384),16384,i*16384};
    Ops ops;PairedSourceIO worker(ops);worker.start();const auto got=worker.read_batch(requests);
    if(ops.peak!=2||ops.calls!=6||ops.active!=0||!ops.third)throw std::runtime_error("The original worker did not refill continuously");
    for(unsigned i=0;i<6;++i)if(got[i]!=16384||static_cast<unsigned char *>(requests[i].target)[16383]!=i+1)
        throw std::runtime_error("Returned source payload differs");
    auto bad=requests;bad[1].target=bad[0].target;bool refused=false;
    try{worker.read_batch(bad);}catch(const std::invalid_argument &){refused=true;}
    if(!refused||ops.calls!=6)throw std::runtime_error("Overlapping delivery reached I/O");
    ops.force=false;const auto pair=worker.read({requests[0],requests[1]});
    if(pair[0]!=16384||pair[1]!=16384||ops.calls!=8)throw std::runtime_error("Original pair API changed after refill");
    unsigned consumed=0;worker.pipeline({requests[0],requests[1]},{16384,16384},[](unsigned){},
        [&](unsigned,const void *){++consumed;});
    if(consumed!=2||ops.calls!=10)throw std::runtime_error("Original synchronous consumer pipeline changed");
    worker.require_completed();worker.stop_completed();
    Ops failure;failure.force=false;failure.short_read=true;PairedSourceIO failed(failure);failed.start();refused=false;
    try{failed.read_batch(requests);}catch(const std::runtime_error &){refused=true;}
    if(!refused||failure.active)throw std::runtime_error("A known short read escaped quarantine");
    failed.stop_completed();
    std::cout<<"{\"same_worker_refill_verified\":true,\"maximum_live_reads\":2,\"original_pair_and_pipeline_preserved\":true,\"invalid_and_short_reads_refused\":true}\n";
}
