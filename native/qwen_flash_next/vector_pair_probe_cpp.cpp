// SPDX-License-Identifier: MIT
#include "completion_probe_io.h"
#include "vectored_source_batch.h"
#include <atomic>
#include <sys/uio.h>
#include <sys/types.h>
#include <unistd.h>
#ifndef QWEN_VECTOR_HOST_STUB
static_assert(sizeof(iovec)==16&&sizeof(off_t)==8,"Qualified native vector ABI");
#endif
extern "C" int completion_probe_source_identity(int,std::uint64_t *,std::uint64_t *,std::uint64_t *);
namespace {
qwen_app::VectoredSourceBatch *reads=nullptr;
std::mutex journal;std::thread::id producer;
std::atomic<std::uint64_t> read_ns{0};std::uint64_t next_id=0;
constexpr unsigned matrix=3276800,stride=3293184;
std::int64_t read_at(void *,const qwen_app::VectoredRead &request) {
    const unsigned slot=std::this_thread::get_id()==producer?0:1;
    {
        std::lock_guard<std::mutex> lock(journal);
        if(!completion_probe_permit())return -1;
        if(!completion_probe_event(0,slot,request.id,request.offset,request.bytes(),0,0,0))
            throw std::runtime_error("Vector pair read admission journal failed");
    }
    const auto begin=completion_probe_now();std::int64_t result=-1;
    if(request.count==1)result=pread(request.fd,request.destinations[0].data,request.destinations[0].bytes,request.offset);
    else {
        struct iovec vectors[3];
        for(unsigned i=0;i<3;++i){vectors[i].iov_base=request.destinations[i].data;vectors[i].iov_len=request.destinations[i].bytes;}
        result=preadv(request.fd,vectors,3,request.offset);
    }
    const auto end=completion_probe_now();
    {
        std::lock_guard<std::mutex> lock(journal);
        if(!begin||end<begin||!completion_probe_event(1,slot,request.id,request.offset,request.bytes(),result,begin,end))
            throw std::runtime_error("Vector pair completion journal failed");
    }
    read_ns.fetch_add(end-begin);return result;
}
}
extern "C" int completion_probe_start() {
    if(reads)return 0;
    try{producer=std::this_thread::get_id();reads=new qwen_app::VectoredSourceBatch(read_at,nullptr);reads->start();return 1;}catch(...){return 0;}
}
extern "C" int completion_probe_batch(int fd,unsigned mode,const completion_extent *extents,unsigned count,
    unsigned char *io,unsigned char *destination,completion_times *times) {
    if(!reads||mode>1||!extents||count!=6||!io||!destination||!times)return 0;
    *times={};read_ns.store(0);
    std::uint64_t device=0,inode=0,file_bytes=0;
    if(!completion_probe_source_identity(fd,&device,&inode,&file_bytes))return 0;
    for(unsigned i=0;i<count;++i)if(extents[i].bytes!=matrix||extents[i].requested!=stride)return 0;
    try {
        const auto begin=completion_probe_now();if(!begin)return 0;
        if(mode==0) {
            for(unsigned wave=0;wave<3;++wave) {
                std::array<qwen_app::VectoredRead,2> requests{};
                for(unsigned lane=0;lane<2;++lane) {
                    const unsigned i=wave*2+lane;auto &r=requests[lane];
                    r.fd=fd;r.device=device;r.inode=inode;r.file_bytes=file_bytes;r.offset=extents[i].offset;
                    r.id=++next_id;r.count=1;r.destinations[0]={destination+i*stride,stride};
                }
                reads->read(requests.data(),2);
            }
        } else {
            std::array<qwen_app::VectoredRead,2> requests{};
            for(unsigned expert=0;expert<2;++expert) {
                auto &r=requests[expert];r.fd=fd;r.device=device;r.inode=inode;r.file_bytes=file_bytes;
                r.offset=extents[expert].offset;r.id=++next_id;r.count=3;
                for(unsigned role=0;role<3;++role) {
                    const unsigned i=role*2+expert;
                    if(extents[i].offset!=r.offset+role*stride)return 0;
                    r.destinations[role]={destination+i*stride,stride};
                }
            }
            reads->read(requests.data(),2);
        }
        const auto end=completion_probe_now();if(end<begin)return -1;
        times->wall_ns=end-begin;times->read_ns=read_ns.load();times->physical_bytes=6u*stride;
        return 1;
    }catch(...){return reads->completion_known()?0:-1;}
}
extern "C" int completion_probe_stop() {
    if(!reads)return 0;
    try{reads->stop_completed();delete reads;reads=nullptr;return 1;}catch(...){return 0;}
}
