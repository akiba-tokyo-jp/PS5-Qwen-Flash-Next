// SPDX-License-Identifier: MIT
#include "completion_probe_io.h"
#include "demand_source_batch.h"
#include <atomic>
#include <sys/types.h>
#include <unistd.h>
namespace {
qwen_app::DemandSourceBatch *reads=nullptr;
std::mutex journal;std::thread::id producer;
std::atomic<std::uint64_t> summed_reads{0};std::uint64_t next_id=0;
constexpr unsigned matrix=3276800,stride=3293184;
std::int64_t read_at(void *,const qwen_app::CompletionRead &r) {
    const unsigned slot=std::this_thread::get_id()==producer?0:1;
    {
        std::lock_guard<std::mutex> lock(journal);
        if(!completion_probe_permit())return -1; // No native read was started.
        if(!completion_probe_event(0,slot,r.id,r.offset,r.bytes,0,0,0))
            throw std::runtime_error("A fresh demand read was not admitted");
    }
    const auto a=completion_probe_now();const auto got=pread(r.fd,r.target,r.bytes,r.offset);const auto b=completion_probe_now();
    {
        std::lock_guard<std::mutex> lock(journal);
        if(!a||b<a||!completion_probe_event(1,slot,r.id,r.offset,r.bytes,got,a,b))
            throw std::runtime_error("A returned demand read was not recorded");
    }
    summed_reads.fetch_add(b-a);return got;
}
}
extern "C" int completion_probe_start() {
    if(reads)return 0;
    try{producer=std::this_thread::get_id();reads=new qwen_app::DemandSourceBatch(read_at,nullptr);reads->start();return 1;}catch(...){return 0;}
}
extern "C" int completion_probe_batch(int fd,unsigned mode,const completion_extent *extents,unsigned count,
    unsigned char *io,unsigned char *destination,completion_times *times) {
    if(!reads||mode>1||!extents||(count!=3&&count!=6)||!io||!destination||!times)return 0;
    *times={};summed_reads.store(0);
    try{
        std::array<qwen_app::CompletionRead,6> requests;
        for(unsigned i=0;i<count;++i){const auto&e=extents[i];
            if(e.bytes!=matrix||e.requested!=matrix||e.offset<(4u<<20)||e.offset+e.requested>(1ull<<30)-(4u<<20))return 0;
            requests[i]={fd,destination+i*stride,e.requested,e.offset,++next_id};
        }
        const auto a=completion_probe_now();if(!a)return 0;
        if(mode==0)for(unsigned i=0;i<count;i+=2)reads->read(requests.data()+i,std::min(2u,count-i));
        else reads->read(requests.data(),count);
        const auto b=completion_probe_now();if(!b||b<a)return -1;
        times->wall_ns=b-a;times->read_ns=summed_reads.load();times->physical_bytes=count*matrix;
        return 1;
    }catch(...){return reads->completion_known()?0:-1;}
}
extern "C" int completion_probe_stop(){if(!reads)return 0;try{reads->stop_completed();delete reads;reads=nullptr;return 1;}catch(...){return 0;}}
