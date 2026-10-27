// SPDX-License-Identifier: MIT
// Current production PairedSourceIO versus a six-demand refill owner.
#include "completion_probe_io.h"
#include "demand_source_batch.h"
#include "paired_source_io.h"
#include <atomic>
#include <sys/types.h>
#include <unistd.h>
namespace {
qwen_app::DemandSourceBatch *refill=nullptr;
qwen_app::PairedSourceIO *paired=nullptr;
std::mutex journal;std::thread::id producer;
std::atomic<std::uint64_t> summed_reads{0};std::uint64_t next_id=0;
constexpr unsigned matrix=3276800,stride=3293184;
std::int64_t logged_read(const qwen_app::CompletionRead &r) {
    const unsigned slot=std::this_thread::get_id()==producer?0:1;
    {
        std::lock_guard<std::mutex> lock(journal);
        if(!completion_probe_permit())return -1;
        if(!completion_probe_event(0,slot,r.id,r.offset,r.bytes,0,0,0))
            throw std::runtime_error("A fresh original read was not admitted");
    }
    const auto a=completion_probe_now();const auto got=pread(r.fd,r.target,r.bytes,r.offset);const auto b=completion_probe_now();
    {
        std::lock_guard<std::mutex> lock(journal);
        if(!a||b<a||!completion_probe_event(1,slot,r.id,r.offset,r.bytes,got,a,b))
            throw std::runtime_error("A returned original read was not recorded");
    }
    summed_reads.fetch_add(b-a);return got;
}
std::int64_t demand_read(void *,const qwen_app::CompletionRead &r){return logged_read(r);}
class OriginalOps final:public qwen_app::SourceReadOps {
public:
    qwen_app::SourceIdentity identity(int)override{throw std::logic_error("Probe identity is owned by the native C guard");}
    int open_direct(const std::string&)override{throw std::logic_error("Probe descriptor is already owned");}
    bool close_file(int)override{throw std::logic_error("Probe descriptor close is owned by the native C guard");}
    std::uint64_t system_headroom()override{return completion_probe_permit()?264ull<<20:0;}
    std::int64_t read_at(int fd,void *target,std::size_t bytes,std::uint64_t offset)override {
        std::uint64_t id;{std::lock_guard<std::mutex> lock(journal);id=++next_id;}
        return logged_read({fd,target,bytes,offset,id});
    }
} original;
}
extern "C" int completion_probe_start() {
    if(refill||paired)return 0;
    try {
        producer=std::this_thread::get_id();
        paired=new qwen_app::PairedSourceIO(original);paired->start();
        refill=new qwen_app::DemandSourceBatch(demand_read,nullptr);refill->start();
        return 1;
    }catch(...){return 0;}
}
extern "C" int completion_probe_batch(int fd,unsigned mode,const completion_extent *extents,unsigned count,
    unsigned char *io,unsigned char *destination,completion_times *times) {
    if(!refill||!paired||mode>1||!extents||count!=6||!io||!destination||!times)return 0;
    *times={};summed_reads.store(0);
    try {
        std::array<qwen_app::CompletionRead,6> requests;
        for(unsigned i=0;i<count;++i){const auto&e=extents[i];
            if(e.bytes!=matrix||e.requested!=matrix||e.offset<(4u<<20)||e.offset+e.requested>(1ull<<30)-(4u<<20))return 0;
            requests[i]={fd,destination+i*stride,e.requested,e.offset,0};
        }
        const auto a=completion_probe_now();if(!a)return 0;
        if(mode==0)for(unsigned i=0;i<count;i+=2) {
            const auto &x=requests[i],&y=requests[i+1];
            const auto result=paired->read({{{fd,x.target,x.bytes,x.offset},{fd,y.target,y.bytes,y.offset}}});
            if(result[0]!=matrix||result[1]!=matrix)return -1;
        }
        else {
            for(auto &r:requests){std::lock_guard<std::mutex> lock(journal);r.id=++next_id;}
            refill->read(requests.data(),count);
        }
        const auto b=completion_probe_now();if(!b||b<a)return -1;
        paired->require_completed();refill->require_completed();
        times->wall_ns=b-a;times->read_ns=summed_reads.load();times->physical_bytes=count*matrix;
        return 1;
    }catch(...){return -1;}
}
extern "C" int completion_probe_stop(){
    if(!refill||!paired)return 0;
    try {
        paired->require_completed();refill->require_completed();
        paired->stop_completed();refill->stop_completed();
        delete paired;paired=nullptr;delete refill;refill=nullptr;return 1;
    }catch(...){return 0;}
}
