// SPDX-License-Identifier: MIT
// Exercise the actual reader and worker: range selection, merged bytes and retained failures.
#include "paired_source_io.h"
#include <atomic>
#include <iostream>
#include <map>
using namespace qwen_app;
static void check(bool value,const char * message){if(!value)throw std::runtime_error(message);}
template<class F> static void rejects(F f){bool failed=false;try{f();}catch(const std::exception&){failed=true;}check(failed,"Unsafe selected source continuation accepted");}
struct Ops:SourceReadOps {
    std::vector<SourceFile> files;
    std::map<int,unsigned> fds;
    std::atomic<unsigned> reads{0},active{0},peak{0};
    std::mutex mutex;std::condition_variable changed;
    bool rendezvous=false;unsigned arrivals=0;int failure=0;bool changed_identity=false;
    std::uint64_t available=512ull<<20;unsigned opened=0;
    PairedSourceIO worker{*this};
    Ops(){for(unsigned i=0;i<2;++i){auto bytes=4ull<<30;files.push_back({"sealed-"+std::to_string(i),bytes,{1,i+1,0100644,1,1,bytes,123,0,123,0}});fds[10+int(i)]=i;}worker.start();}
    ~Ops()override{worker.stop_completed();}
    SourceIdentity identity(int fd)override{auto id=files[fds.at(fd)].identity;if(changed_identity)++id[8];return id;}
    int open_direct(const std::string& path)override{for(unsigned i=0;i<2;++i)if(path==files[i].path){int fd=100+int(++opened);fds[fd]=i;return fd;}return -1;}
    bool close_file(int fd)override{check(active==0,"In-flight file closed");return fds.erase(fd)==1;}
    std::uint64_t system_headroom()override{return available;}
    std::int64_t read_at(int fd,void * target,std::size_t bytes,std::uint64_t offset)override{
        ++reads;auto count=++active;auto old=peak.load();while(count>old&&!peak.compare_exchange_weak(old,count)){}
        struct Leave{std::atomic<unsigned>& active;~Leave(){--active;}}leave{active};
        if(rendezvous){std::unique_lock<std::mutex> lock(mutex);++arrivals;changed.notify_all();check(changed.wait_for(lock,std::chrono::seconds(3),[&]{return arrivals>=2;}),"Selected reads did not overlap");}
        if(failure==2&&target==first_target)throw std::runtime_error("Injected producer read error");
        auto * p=static_cast<unsigned char*>(target);const auto file=fds.at(fd);
        for(std::size_t i=0;i<bytes;++i)p[i]=(offset+i+17*file)%251;
        return std::int64_t(bytes)-(failure==1?1:0);
    }
    void * first_target=nullptr;
    std::array<std::int64_t,2> read_pair(const std::array<SourceReadRequest,2>& r)override{first_target=r[0].target;return worker.read(r);}
    SourcePipelineTimes pipeline_pair(const std::array<SourceReadRequest,2>& r,const std::array<std::uint64_t,2>& expected,
            const std::function<void(unsigned)>& before,const std::function<void(unsigned,const void*)>& consume)override{return worker.pipeline(r,expected,before,consume);}
};
struct Fixture {
    static constexpr std::uintptr_t a=512ull<<30,b=a+(8ull<<30);
    static constexpr std::size_t bytes=3276800;
    Ops ops;std::vector<unsigned char> storage;unsigned char * scratch;MappedSourceReader reader;
    Fixture():storage(model_read_window+3*model_read_alignment,0xa5),
        scratch(reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(storage.data())+2*model_read_alignment-1)&~std::uintptr_t(model_read_alignment-1))),
        reader(ops.files,ops,scratch){reader.register_mapping(a,ops.files[0].bytes,10);reader.register_mapping(b,ops.files[1].bytes,11);}
    void consume(unsigned index,const void * source,const std::array<std::uint64_t,2>& offsets,const std::array<unsigned,2>& files,unsigned& calls){
        check(index==calls++,"Consumer ordering or cache destination changed");
        for(std::size_t i=0;i<bytes;++i)check(static_cast<const unsigned char*>(source)[i]==(offsets[index]+i+17*files[index])%251,"Original expert byte changed");
        check(!reader.stats().completed_windows,"A live source lease was published early");
    }
    void canaries(){for(unsigned i=0;i<model_read_alignment;++i)check(scratch[-int(i)-1]==0xa5&&scratch[model_read_window+i]==0xa5,"Source window exceeded 8 MiB");}
};
int main(){try{
    {Ops ops;auto id=ops.files[0].identity,alias=id;alias[8]++;
     constexpr auto G=source_schedule_region_bytes,M=source_schedule_boundary_margin;
     check(!source_schedule_extent(M-16384,16384,id)&&source_schedule_extent(M,16384,id),"Lower boundary guard changed");
     check(source_schedule_extent(G-M-16384,16384,id)&&!source_schedule_extent(G-M,16384,id),"Full upper extent guard changed");
     check(!source_schedule_extent(G-16384,32768,id)&&!source_schedule_extent(UINT64_MAX-1,16384,id),"Crossing/overflow extent accepted");
     check(!source_schedule_parallel(id,100ull<<20,16384,alias,(G+100*(1ull<<20)),16384),"Same-inode aliases bypassed region protection");
     alias[0]=0;check(!source_schedule_parallel(id,100ull<<20,16384,alias,200ull<<20,16384),"Unknown file identity accepted");}
    {Fixture f;f.reader.qualify_source_schedule();check(f.reader.stats().parallel_batches==1&&f.reader.stats().coalesced_batches==1,"Actual pre-backend CPU qualification was incomplete");f.canaries();}
    for(unsigned pattern=0;pattern<4;++pattern){Fixture f;f.reader.enable_source_schedule();
        std::array<std::uint64_t,2> offsets{(100ull<<20)+2784,(200ull<<20)+1632};
        std::array<unsigned,2> files{0,pattern==1?1u:0u};
        if(pattern==2)offsets[1]=(1100ull<<20)+1632;
        if(pattern==3)offsets[1]=offsets[0]+Fixture::bytes;
        f.ops.rendezvous=pattern<2;unsigned calls=0;
        f.reader.upload_pair({Fixture::a+offsets[0],(files[1]?Fixture::b:Fixture::a)+offsets[1]},Fixture::bytes,
            [&](unsigned i,const void * p){f.consume(i,p,offsets,files,calls);});
        check(calls==2&&f.reader.stats().completed_windows==2,"Selected source pair did not complete");
        if(pattern<2)check(f.ops.peak==2&&f.reader.stats().parallel_batches==1,"Qualified parallel path absent");
        if(pattern==2)check(f.ops.peak==1&&f.reader.stats().selected_serial_batches==1,"Cross-region source reads overlapped");
        if(pattern==3)check(f.ops.reads==1&&f.reader.stats().coalesced_batches==1,"Adjacent sources were not coalesced");
        check(f.reader.stats().physical_read_calls==(pattern==3?1u:2u),"Physical calls fabricated");f.canaries();
    }
    {Fixture f;unsigned calls=0;f.reader.upload_pair({Fixture::a+(100ull<<20),Fixture::a+(200ull<<20)},Fixture::bytes,[&](unsigned,const void*){++calls;});
     check(calls==2&&f.ops.peak==1&&!f.reader.stats().parallel_batches,"Default source policy changed");}
    for(int failure=0;failure<6;++failure){Fixture f;f.reader.enable_source_schedule();unsigned consumers=0;
        const auto offset=(100ull<<20)+2784;const bool merged=failure<2;
        if(failure==0||failure==2)f.ops.failure=1;if(failure==3)f.ops.failure=2;
        if(failure==4)f.ops.changed_identity=true;if(failure==5)f.ops.available=0;
        rejects([&]{f.reader.upload_pair({Fixture::a+offset,Fixture::a+(merged?offset+Fixture::bytes:offset+10*(1ull<<20))},Fixture::bytes,
            [&](unsigned,const void*){++consumers;if(failure==1)throw std::runtime_error("Injected completed consumer error");});});
        auto reads=f.ops.reads.load();check(!f.ops.active&&!f.reader.stats().completed_windows,"Failed source pair was retired or published");
        rejects([&]{f.reader.require_completed_window();});rejects([&]{f.reader.upload_pair({Fixture::a+offset,Fixture::b+offset},Fixture::bytes,[](unsigned,const void*){});});
        check(f.ops.reads==reads,"Failed source pair retried");f.canaries();
    }
    std::cout<<"Full-range selection, actual parallel/serial execution, merged original bytes, unchanged default and retained failures passed\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
