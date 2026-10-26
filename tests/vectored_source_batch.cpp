// SPDX-License-Identifier: MIT
#include "vectored_source_batch.h"
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

namespace {
void check(bool value){if(!value)throw std::runtime_error("Vectored owner control failed");}
template<class F> void refuses(F fn){bool caught=false;try{fn();}catch(const std::exception&){caught=true;}check(caught);}
struct State {
    std::mutex mutex;std::condition_variable changed;
    unsigned arrived=0,active=0,peak=0,calls=0,expected=2;
    bool shortened=false,throwing=false,refused=false,reentrant=false;
    qwen_app::VectoredSourceBatch *owner=nullptr;
    std::thread::id producer=std::this_thread::get_id();
};
std::int64_t reader(void *opaque,const qwen_app::VectoredRead &r) {
    auto &s=*static_cast<State *>(opaque);
    {
        std::unique_lock<std::mutex> lock(s.mutex);++s.arrived;++s.active;++s.calls;
        if(s.active>s.peak)s.peak=s.active;
        s.changed.notify_all();
        check(s.changed.wait_for(lock,std::chrono::seconds(5),[&]{return s.arrived==s.expected;}));
    }
    if(s.reentrant&&std::this_thread::get_id()==s.producer)
        refuses([&]{s.owner->read(&r,1);});
    for(unsigned i=0;i<r.count;++i)std::memset(r.destinations[i].data,static_cast<unsigned char>(r.id+i),r.destinations[i].bytes);
    {std::lock_guard<std::mutex> lock(s.mutex);--s.active;}
    if(s.throwing)throw std::runtime_error("Synthetic unknown reader completion");
    if(s.refused)return -1;
    return static_cast<std::int64_t>(r.bytes()-(s.shortened?16384:0));
}
std::array<qwen_app::VectoredRead,2> requests(unsigned char *base) {
    std::array<qwen_app::VectoredRead,2> r{};
    for(unsigned i=0;i<2;++i) {
        r[i].fd=17;r[i].device=7;r[i].inode=31;r[i].file_bytes=64u<<20;
        r[i].offset=(4u<<20)+16384+(i<<20);r[i].id=i+1;r[i].count=3;
        for(unsigned j=0;j<3;++j)r[i].destinations[j]={base+(2*j+i)*32768,16384};
    }
    return r;
}
}
int main(int argc,char **argv) {
    const bool unknown=argc==2&&std::strcmp(argv[1],"--unknown")==0;
    check(argc==1||unknown);
    auto *backing=new std::vector<unsigned char>(6*32768+16383,0xa7);
    auto *base=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(backing->data())+16383)&~std::uintptr_t(16383));
    auto r=requests(base);
    if(unknown) {
        auto *state=new State;state->throwing=true;
        auto *owner=new qwen_app::VectoredSourceBatch(reader,state);state->owner=owner;owner->start();
        refuses([&]{owner->read(r.data(),2);});check(!owner->completion_known());
        refuses([&]{owner->stop_completed();});
        std::printf("{\"unknown_completion_retains_owner_worker_and_destinations\":true,\"PS5_operations\":0}\n");
        std::fflush(stdout);
        // Isolated host fault-control process: do not invoke retained destructors.
        std::_Exit(0);
    }
    State state;qwen_app::VectoredSourceBatch owner(reader,&state);state.owner=&owner;owner.start();
    unsigned refused=0;
    auto reject=[&](std::array<qwen_app::VectoredRead,2> changed){refuses([&]{owner.read(changed.data(),2);});++refused;check(state.calls==0);};
    auto bad=r;bad[0].count=2;reject(bad);
    bad=r;bad[0].fd=-1;reject(bad);
    bad=r;bad[0].device=0;reject(bad);
    bad=r;bad[0].inode=0;reject(bad);
    bad=r;bad[0].file_bytes=0;reject(bad);
    bad=r;bad[0].file_bytes=(512ull<<20)+16384;reject(bad);
    bad=r;bad[0].offset=bad[0].file_bytes-16384;reject(bad);
    bad=r;bad[0].offset=UINT64_MAX-16383;reject(bad);
    bad=r;bad[0].offset=(4u<<20)-16384;reject(bad);
    bad=r;bad[0].destinations[0].data=nullptr;reject(bad);
    bad=r;bad[0].destinations[0].data=base+1;reject(bad);
    bad=r;bad[0].destinations[0].bytes=0;reject(bad);
    bad=r;bad[0].destinations[0].bytes=16385;reject(bad);
    bad=r;bad[0].destinations[0].bytes=(4u<<20)+16384;reject(bad);
    bad=r;bad[0].destinations[0]={reinterpret_cast<void *>(UINTPTR_MAX-16383),32768};reject(bad);
    bad=r;bad[0].destinations[1]=bad[0].destinations[0];reject(bad);
    bad=r;bad[1].destinations[0]=bad[0].destinations[0];reject(bad);
    bad=r;bad[1].device=8;reject(bad);
    bad=r;bad[1].inode=32;reject(bad);
    bad=r;bad[1].file_bytes-=16384;reject(bad);
    bad=r;bad[1].id=bad[0].id;reject(bad);
    refuses([&]{owner.read(nullptr,2);});++refused;
    refuses([&]{owner.read(r.data(),3);});++refused;
    std::thread other([&]{refuses([&]{owner.read(r.data(),2);});});other.join();
    state.reentrant=true;owner.read(r.data(),2);check(owner.completion_known()&&state.peak==2&&state.calls==2);
    for(unsigned job=0;job<2;++job)for(unsigned v=0;v<3;++v) {
        const auto *p=static_cast<unsigned char *>(r[job].destinations[v].data);
        for(unsigned i=0;i<16384;++i)check(p[i]==r[job].id+v&&p[i+16384]==0xa7);
    }
    state.reentrant=false;state.arrived=0;state.calls=0;
    auto scalar=r;scalar[0].count=scalar[1].count=1;
    owner.read(scalar.data(),2);check(owner.completion_known()&&state.calls==2);
    state.arrived=0;state.calls=0;state.expected=1;
    auto single=r;single[0].offset=0;
    owner.read(single.data(),1);check(owner.completion_known()&&state.calls==1);
    state.arrived=0;state.calls=0;state.expected=2;
    auto different=r;different[0].offset=0;different[1].offset=0;different[1].fd=18;different[1].inode=32;
    owner.read(different.data(),2);check(owner.completion_known()&&state.calls==2);
    owner.stop_completed();
    for(unsigned failure=0;failure<2;++failure) {
        State next;next.shortened=failure==0;next.refused=failure==1;
        qwen_app::VectoredSourceBatch failed(reader,&next);next.owner=&failed;failed.start();
        refuses([&]{failed.read(r.data(),2);});check(failed.completion_known());failed.stop_completed();
    }
    delete backing;
    std::printf("{\"invalid_requests_refused_before_IO\":%u,\"parallel_calls\":2,\"all_six_destinations_exact\":true,\"tail_canaries\":true,\"scalar_pair_and_single_vector_checked\":true,\"distinct_files_same_device_checked\":true,\"reentrant_and_wrong_producer_refused\":true,\"returned_failures_joined\":2,\"PS5_operations\":0}\n",refused);
}
