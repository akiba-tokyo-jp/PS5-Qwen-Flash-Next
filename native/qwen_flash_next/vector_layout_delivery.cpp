// SPDX-License-Identifier: MIT
#include "vector_layout_delivery.h"
#include "vectored_source_batch.h"
#include "batch_io_journal.h"
#include <string>
#include <sys/uio.h>
#include <sys/types.h>
#include <unistd.h>
#ifndef QWEN_VECTOR_HOST_STUB
static_assert(sizeof(iovec)==16&&sizeof(off_t)==8,"Qualified native vector ABI");
#endif
namespace {
using namespace qwen_app;
constexpr unsigned stride=3293184;
VectoredSourceBatch *reads=nullptr;BatchIOJournal *events=nullptr;
std::mutex admission;std::uint64_t next_id=0;
void persist(const std::string &text) {
    if(text.size()>1000||!vector_layout_record(text.c_str()))throw std::runtime_error("Compact layout safety record failed; backing retained");
}
std::int64_t read_at(void *,const VectoredRead &r) {
    {std::lock_guard<std::mutex> lock(admission);if(!vector_layout_permit())throw std::runtime_error("Layout read headroom refused");}
    const auto begin=vector_layout_now();events->begin(r.id,r.offset,r.bytes(),begin);
    ssize_t got;
    if(r.count==1)got=pread(r.fd,r.destinations[0].data,r.destinations[0].bytes,r.offset);
    else {
        iovec vectors[3];for(unsigned i=0;i<3;++i){vectors[i].iov_base=r.destinations[i].data;vectors[i].iov_len=r.destinations[i].bytes;}
        got=preadv(r.fd,vectors,3,r.offset);
    }
    events->returned(r.id,got,vector_layout_now());return got;
}
void returned_snapshot() {
    const auto s=events->snapshot();std::string text="LAYOUT_RETURNED count="+std::to_string(s.count)+" uncertain="+std::to_string(s.uncertain)+" events=";
    for(unsigned i=0;i<s.count;++i){const auto &e=s.events[i];if(i)text+=",";
        text+=std::to_string(e.plan.id)+":"+std::to_string(e.plan.offset)+":"+std::to_string(e.plan.bytes)+":"+
            std::to_string(e.begun)+":"+std::to_string(e.returned)+":"+std::to_string(e.result)+":"+
            std::to_string(e.begin_ns)+":"+std::to_string(e.end_ns);}
    persist(text);
}
}
extern "C" int vector_layout_start() {
    if(reads||events)return 0;
    try {events=new BatchIOJournal;reads=new VectoredSourceBatch(read_at,nullptr);reads->start();return 1;}catch(...){return 0;}
}
extern "C" int vector_layout_batch(unsigned mode,const vector_layout_source sources[6],unsigned char *destination,vector_layout_times *times) {
    if(!reads||!events||mode>1||!sources||!destination||!times)return 0;
    *times={};std::array<VectoredRead,6> requests{};std::array<BatchIOPlan,6> plans{};
    const unsigned count=mode?2:6;
    try {
        const auto begin=vector_layout_now();if(!begin)return 0;
        for(unsigned i=0;i<count;++i) {
            auto &r=requests[i];r.fd=sources[i].fd;r.offset=sources[i].offset;r.id=next_id+i+1;r.count=mode?3:1;
            if(!vector_layout_identity(r.fd,&r.device,&r.inode,&r.file_bytes))return 0;
            for(unsigned j=0;j<r.count;++j)r.destinations[j]={destination+((mode?j*2+i:i)*stride),stride};
            if(mode)for(unsigned role=1;role<3;++role)
                if(sources[role*2+i].fd!=r.fd||sources[role*2+i].offset!=r.offset+role*stride)return 0;
            plans[i]={r.id,r.offset,r.bytes()};
        }
        events->prepare(plans.data(),count);std::string text="LAYOUT_PLAN mode="+std::to_string(mode)+" events=";
        for(unsigned i=0;i<count;++i){if(i)text+=",";text+=std::to_string(plans[i].id)+":"+std::to_string(plans[i].offset)+":"+std::to_string(plans[i].bytes);}
        persist(text);events->admit_durable();next_id+=count;
        const auto source_begin=vector_layout_now();
        try{for(unsigned wave=0;wave<(mode?1u:3u);++wave)reads->read(requests.data()+wave*2,2);}
        catch(...){if(!reads->completion_known())events->retain_uncertain();returned_snapshot();throw;}
        const auto source_end=vector_layout_now();returned_snapshot();events->finish_after_durable_return();const auto end=vector_layout_now();
        if(source_begin<begin||source_end<=source_begin||end<source_end)throw std::runtime_error("Layout interval clock refused");
        times->wall_ns=end-begin;times->source_ns=source_end-source_begin;times->physical_bytes=6u*stride;return 1;
    }catch(...){return reads->completion_known()?0:-1;}
}
extern "C" int vector_layout_stop() {
    if(!reads)return 0;
    try{reads->stop_completed();delete reads;reads=nullptr;delete events;events=nullptr;return 1;}catch(...){return 0;}
}
