// SPDX-License-Identifier: MIT
#include "queued_source_io.h"
#include <atomic>
#include <cstdlib>
#include <iostream>
using namespace qwen_app;
static void check(bool ok){if(!ok)throw std::runtime_error("Queued source control failed");}
struct Ops:SourceReadOps {
    std::mutex mutex;std::condition_variable changed;
    unsigned entered=0,expected=4;std::atomic<unsigned> active{0},reads{0};
    int fail_fd=-1;bool delay=false;
    SourceIdentity identity(int)override{return {};}
    int open_direct(const std::string &)override{return -1;}
    bool close_file(int)override{check(active==0);return true;}
    std::uint64_t system_headroom()override{return 512ull<<20;}
    std::int64_t read_at(int fd,void *target,std::size_t bytes,std::uint64_t offset)override{
        ++reads;++active;struct Leave{std::atomic<unsigned>& active;~Leave(){--active;}}leave{active};
        {std::unique_lock<std::mutex> lock(mutex);++entered;changed.notify_all();
         check(changed.wait_for(lock,std::chrono::seconds(3),[&]{return entered>=expected;}));}
        if(delay && fd==13)std::this_thread::sleep_for(std::chrono::seconds(12));
        if(fd==fail_fd)throw std::runtime_error("Injected completed read exception");
        auto *out=static_cast<unsigned char*>(target);
        for(std::size_t i=0;i<bytes;++i)out[i]=static_cast<unsigned char>((offset+i+fd)%251);
        return bytes;
    }
};
int main(int argc,char**) {
    std::vector<unsigned char> storage(model_read_window+model_read_alignment);
    void *memory=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(storage.data())+
        model_read_alignment-1)&~std::uintptr_t(model_read_alignment-1));
    Ops ops;auto *queue=new QueuedSourceIO(ops);queue->start();
    std::array<SourceReadRequest,4> requests{};
    for(unsigned i=0;i<4;++i)requests[i]={10+int(i),static_cast<unsigned char*>(memory)+(2u<<20)*i,2u<<20,16384u*i};
    if(argc>1){ops.delay=true;bool rejected=false;
        try{queue->read(requests,4);}catch(const std::exception &){rejected=true;}
        check(rejected && ops.active>0);std::cout<<"Unknown backing retained without destructor or close\n"<<std::flush;
        std::_Exit(0);}
    auto values=queue->read(requests,4);check(ops.active==0 && ops.reads==4);
    for(unsigned i=0;i<4;++i){check(values[i]==2u<<20);const auto *b=static_cast<unsigned char*>(requests[i].target);
        check(b[0]==(requests[i].offset+10+i)%251 && b[(2u<<20)-1]==(requests[i].offset+(2u<<20)-1+10+i)%251);}
    ops.entered=0;ops.expected=2;requests[1].target=static_cast<unsigned char*>(memory)+(4u<<20);
    requests[0].bytes=requests[1].bytes=4u<<20;values=queue->read(requests,2);check(ops.active==0 && ops.reads==6);
    auto rejected=[&](auto input,unsigned count){const auto before=ops.reads.load();bool caught=false;
        try{queue->read(input,count);}catch(const std::exception &){caught=true;}check(caught && ops.reads==before);};
    rejected(requests,3);auto invalid=requests;invalid[1].target=invalid[0].target;rejected(invalid,2);
    invalid=requests;invalid[0].bytes+=16384;rejected(invalid,2);
    invalid=requests;invalid[0].offset=1;rejected(invalid,2);
    invalid=requests;invalid[0].target=static_cast<unsigned char*>(memory)+1;rejected(invalid,2);
    invalid=requests;invalid[0].fd=-1;rejected(invalid,2);
    invalid=requests;invalid[0].bytes=0;rejected(invalid,2);
    ops.entered=0;ops.expected=2;ops.fail_fd=11;bool caught=false;
    try{queue->read(requests,2);}catch(const std::exception &){caught=true;}
    check(caught && ops.active==0);queue->stop_completed();delete queue;
    std::cout<<"Four/two-read exact bytes, seven dispatch refusals and completed-exception shutdown passed\n";
}
