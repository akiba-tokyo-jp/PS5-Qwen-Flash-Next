// SPDX-License-Identifier: MIT
// Exercise the exact application's two-read executor, without any GPU/model.
#include "source_contention_probe_io.h"
#include "paired_source_io.h"
namespace {
class TimedOps final : public qwen_app::SourceReadOps {
public:
    job * jobs = nullptr;
    bool noop = false;
    qwen_app::SourceIdentity identity(int) override {throw std::logic_error("Unused probe identity path");}
    int open_direct(const std::string &) override {throw std::logic_error("Unused probe open path");}
    bool close_file(int) override {throw std::logic_error("Unused probe close path");}
    std::uint64_t system_headroom() override {throw std::logic_error("Unused probe headroom path");}
    std::int64_t read_at(int fd,void * target,std::size_t bytes,std::uint64_t offset) override {
        const unsigned index=target==jobs[0].target?0:1;
        auto & j=jobs[index];
        if(j.target!=target||j.fd!=fd||j.bytes!=bytes||std::uint64_t(j.offset)!=offset)
            throw std::logic_error("The probe's actual executor changed a read request");
        probe_execute_read(&j,index,noop);
        return j.sample.got;
    }
};
TimedOps ops;
qwen_app::PairedSourceIO * executor=nullptr;
}
extern "C" int probe_cpp_start() {
    try {executor=new qwen_app::PairedSourceIO(ops);executor->start();return 1;}catch(...){return 0;}
}
extern "C" int probe_cpp_read(job * jobs,int noop) {
    try {
        ops.jobs=jobs;ops.noop=noop;
        std::array<qwen_app::SourceReadRequest,2> r{};
        for(unsigned i=0;i<2;++i)r[i]={jobs[i].fd,jobs[i].target,jobs[i].bytes,std::uint64_t(jobs[i].offset)};
        const auto got=executor->read(r);
        return got[0]==ssize_t(jobs[0].bytes)&&got[1]==ssize_t(jobs[1].bytes);
    }catch(...){return 0;}
}
extern "C" int probe_cpp_stop() {
    try {executor->stop_completed();delete executor;executor=nullptr;return 1;}catch(...){return 0;}
}
