// SPDX-License-Identifier: MIT
#include "completion_probe_io.h"
#include "completion_source_io.h"
#include "bf16_decode_queue.h"
#include <sys/types.h>
#include <unistd.h>

namespace {
constexpr size_t slot_bytes=4u<<20;
constexpr size_t exponent_bytes=QWEN_BF16_MATRIX_MAX/2;
constexpr size_t input_bytes=slot_bytes-exponent_bytes;
std::mutex journal;
qwen_app::CompletionSourceIO *reads=nullptr;
qwen_app::BF16DecodeQueue *decoder=nullptr;
std::array<uint64_t,2> read_ns{};
uint64_t next_id=0;
int event(unsigned returned,unsigned slot,const qwen_app::CompletionRead &r,int64_t got,uint64_t a,uint64_t b) {
    std::lock_guard<std::mutex> lock(journal);
    return completion_probe_event(returned,slot,r.id,r.offset,r.bytes,got,a,b);
}
int64_t read_at(void *,unsigned slot,const qwen_app::CompletionRead &r) {
    if(!event(0,slot,r,0,0,0))throw std::runtime_error("A read intent was not persisted");
    const auto a=completion_probe_now();
    const auto got=pread(r.fd,r.target,r.bytes,r.offset);
    const auto b=completion_probe_now();
    if(!event(1,slot,r,got,a,b)||!a||b<a)throw std::runtime_error("A returned read was not recorded");
    read_ns[slot]=b-a;return got;
}
}
extern "C" int completion_probe_start() {
    if(reads||decoder)return 0;
    try {
        reads=new qwen_app::CompletionSourceIO(read_at,nullptr);reads->start();
        decoder=new qwen_app::BF16DecodeQueue;decoder->start();return 1;
    }catch(...){return 0;}
}
extern "C" int completion_probe_batch(int fd,unsigned mode,const completion_extent *extents,unsigned count,
    unsigned char *io,unsigned char *destination,completion_times *times) {
    if(!reads||!decoder||mode>=6||!extents||(count!=3&&count!=9)||!io||!destination||!times)return 0;
    *times={};const bool packed=mode>=4,compressed=mode>=2&&mode<4,continuous=mode%2;
    try {
        for(unsigned i=0;i<count;++i) {
            const auto &e=extents[i];
            if(!e.bytes||e.bytes>e.requested||e.requested>(compressed?input_bytes:QWEN_BF16_MATRIX_MAX)||
               e.offset<(4u<<20)||e.offset+e.requested>(1ull<<30)-(4u<<20)||
               (!compressed&&(e.bytes!=QWEN_BF16_MATRIX_MAX||e.requested!=e.bytes)))return 0;
        }
        std::array<completion_extent,9> planned{};
        for(unsigned i=0;i<count;++i)planned[i]=extents[i];
        if(packed) {
            if(count!=3)return 0;
            for(unsigned i=0;i<count;++i) {
                if(extents[i].offset!=extents[0].offset+i*QWEN_BF16_MATRIX_MAX)return 0;
                const unsigned bytes=i<2?static_cast<unsigned>(slot_bytes):count*QWEN_BF16_MATRIX_MAX-2*slot_bytes;
                planned[i]={extents[0].offset+i*slot_bytes,bytes,bytes};
            }
        }
        unsigned next=0,done=0,live=0;
        std::array<unsigned,2> sample{};
        auto submit=[&](unsigned slot) {
            const auto i=next++;const auto &e=planned[i];
            if(!completion_probe_permit())throw std::runtime_error("Source headroom refused");
            sample[slot]=i;
            reads->submit(slot,{fd,(compressed||packed)?io+slot*slot_bytes:destination+i*QWEN_BF16_MATRIX_MAX,
                e.requested,e.offset,++next_id});++live;
        };
        const auto a=completion_probe_now();if(!a)return 0;
        while(done<count) {
            if(!live)for(unsigned slot=0;slot<2&&next<count;++slot)submit(slot);
            const auto result=reads->take(!continuous);const unsigned slot=result.slot,i=sample[slot];
            if(result.bytes!=static_cast<int64_t>(planned[i].requested))throw std::runtime_error("Source result differs");
            times->read_ns+=read_ns[slot];times->physical_bytes+=result.request.bytes;
            if(compressed) {
                auto *input=io+slot*slot_bytes;auto *output=destination+i*QWEN_BF16_MATRIX_MAX;
                qwen_bf16_decode_plan plan;
                const auto c=completion_probe_now();
                if(!qwen_bf16_prepare(input,extents[i].bytes,output,QWEN_BF16_MATRIX_MAX,
                    input+input_bytes,exponent_bytes,&plan)||!decoder->decode(plan))
                    throw std::runtime_error("Original BF16 reconstruction failed");
                const auto d=completion_probe_now();if(!c||d<c)throw std::runtime_error("Clock result differs");
                times->restore_ns+=d-c;
            }
            if(packed) {
                const auto c=completion_probe_now();
                memcpy(destination+i*slot_bytes,io+slot*slot_bytes,planned[i].bytes);
                const auto d=completion_probe_now();if(!c||d<c)throw std::runtime_error("Copy clock result differs");
                times->copy_ns+=d-c;
            }
            reads->release(slot);--live;++done;
            if(continuous&&next<count)submit(slot);
        }
        const auto b=completion_probe_now();if(!b||b<a||live)return -1;
        times->wall_ns=b-a;return 1;
    }catch(...){return -1;}
}
extern "C" int completion_probe_stop() {
    if(!reads||!decoder)return 0;
    try {
        reads->stop_completed();decoder->stop_completed();delete reads;delete decoder;
        reads=nullptr;decoder=nullptr;return 1;
    }catch(...){return 0;}
}
