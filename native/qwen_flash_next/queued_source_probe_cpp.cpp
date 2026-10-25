// SPDX-License-Identifier: MIT
#include "queued_source_io.h"
#include "queued_source_probe_io.h"
#include <atomic>
#include <unistd.h>
namespace {
std::atomic<unsigned> pending{0};
struct Ops:qwen_app::SourceReadOps {
    qwen_app::SourceIdentity identity(int)override{return {};}
    int open_direct(const std::string &)override{return -1;}
    bool close_file(int)override{return false;}
    std::uint64_t system_headroom()override{return 0;}
    std::int64_t read_at(int fd,void *target,std::size_t bytes,std::uint64_t offset)override{
        pending.fetch_add(1,std::memory_order_release);
        const auto result=pread(fd,target,bytes,static_cast<off_t>(offset));
        pending.fetch_sub(1,std::memory_order_release);return result;
    }
}ops;
qwen_app::QueuedSourceIO *queue=nullptr;
}
extern "C" int queued_probe_start() {
    if(queue)return 0;
    try {queue=new qwen_app::QueuedSourceIO(ops);queue->start();return 1;}catch(...){return 0;}
}
extern "C" int queued_probe_read(const queued_probe_request *input,unsigned count,int64_t *output) {
    if(!queue || !input || !output || (count!=2 && count!=4))return 0;
    std::array<qwen_app::SourceReadRequest,4> requests{};
    for(unsigned i=0;i<count;++i)requests[i]={input[i].fd,input[i].target,input[i].bytes,input[i].offset};
    try {const auto result=queue->read(requests,count);for(unsigned i=0;i<count;++i)output[i]=result[i];return 1;}
    catch(...){return 0;}
}
extern "C" int queued_probe_stop() {
    if(!queue || pending.load(std::memory_order_acquire))return 0;
    try {queue->stop_completed();delete queue;queue=nullptr;return 1;}catch(...){return 0;}
}
extern "C" unsigned queued_probe_pending(){return pending.load(std::memory_order_acquire);}
