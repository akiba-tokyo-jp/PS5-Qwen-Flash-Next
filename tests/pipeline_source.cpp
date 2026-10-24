// SPDX-License-Identifier: MIT
// Real worker handoff: one read, original bytes, overlap and retained failures.
#include "paired_source_io.h"
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <map>
using namespace qwen_app;
static void check(bool ok,const char * message) { if(!ok)throw std::runtime_error(message); }
template<class F> static void rejected(F f) { bool failed=false;try {f();}catch(const std::exception &){failed=true;}check(failed,"Unsafe pipeline accepted"); }
struct Ops final : SourceReadOps {
    std::vector<SourceFile> files;
    std::map<int,std::size_t> descriptors;
    std::atomic<unsigned> reads{0},active{0},peak{0};
    std::mutex mutex;std::condition_variable changed;
    bool overlap=false,helper_entered=false,consumer_entered=false;
    unsigned opens=0,closes=0;int failure=0;bool identity_changed=false;
    std::uint64_t available=512ull<<20;void * half=nullptr;
    PairedSourceIO worker{*this};
    Ops() {
        for(unsigned i=0;i<2;++i) {
            const std::uint64_t bytes=3*model_read_window+1000;
            files.push_back({"sealed-"+std::to_string(i),bytes,{1,i+1,0100644,0,0,bytes,123,0,123,0}});
            descriptors[10+int(i)]=i;
        }
        worker.start();
    }
    ~Ops() override {worker.stop_completed();}
    SourceIdentity identity(int fd) override {auto r=files.at(descriptors.at(fd)).identity;if(identity_changed)++r[8];return r;}
    int open_direct(const std::string & path) override {
        for(std::size_t i=0;i<files.size();++i)if(files[i].path==path){int fd=100+int(++opens);descriptors[fd]=i;return fd;}
        return -1;
    }
    bool close_file(int fd) override {check(!active,"Closed in-flight source");++closes;return descriptors.erase(fd)==1;}
    std::uint64_t system_headroom() override {return available;}
    std::int64_t read_at(int fd,void * target,std::size_t bytes,std::uint64_t offset) override {
        ++reads;const auto current=++active;auto old=peak.load();while(current>old&&!peak.compare_exchange_weak(old,current)){}
        struct Leave {std::atomic<unsigned> & x;~Leave(){--x;}} leave{active};
        check(current==1,"Two storage reads overlapped");
        const bool helper=target==half;
        if(helper&&overlap) {
            std::unique_lock<std::mutex> lock(mutex);helper_entered=true;changed.notify_all();
            check(changed.wait_for(lock,std::chrono::seconds(5),[&]{return consumer_entered;}),"Worker did not overlap the producer consumer");
        }
        if(helper&&failure==2)throw std::runtime_error("Injected helper failure");
        if(!helper&&failure==3)return -1;
        if(helper&&failure==6)std::this_thread::sleep_for(std::chrono::seconds(12));
        const auto file=descriptors.at(fd),count=std::min<std::uint64_t>(bytes,files[file].bytes-offset);
        auto * p=static_cast<unsigned char *>(target);
        for(std::size_t i=0;i<count;++i)p[i]=(offset+i+17*file)%251;
        return std::int64_t(count)-((helper&&failure==1)?1:0);
    }
    SourcePipelineTimes pipeline_pair(const std::array<SourceReadRequest,2> & req,const std::array<std::uint64_t,2> & expected,
            const std::function<void(unsigned)> & before,const std::function<void(unsigned,const void*)> & consume) override {
        half=req[1].target;
        return worker.pipeline(req,expected,before,consume);
    }
    void consume(unsigned index,const void * p,std::size_t offset,std::size_t bytes) {
        if(index==0&&overlap) {
            std::unique_lock<std::mutex> lock(mutex);consumer_entered=true;changed.notify_all();
            check(changed.wait_for(lock,std::chrono::seconds(5),[&]{return helper_entered;}),"Consumer serialized the future read");
        }
        if(failure==int(index)+4)throw std::runtime_error("Injected synchronous consumer failure");
        for(std::size_t i=0;i<bytes;++i)check(static_cast<const unsigned char*>(p)[i]==(offset+i+17*index)%251,"Original source byte changed");
    }
};
int main(int argc,char ** argv) {
    try {
        std::vector<unsigned char> storage(model_read_window+3*model_read_alignment,0xa5);
        auto at=reinterpret_cast<std::uintptr_t>(storage.data());
        auto * scratch=reinterpret_cast<unsigned char*>((at+2*model_read_alignment-1)&~(std::uintptr_t(model_read_alignment)-1));
        constexpr std::uintptr_t a=512ull<<30,b=a+(64ull<<20);constexpr std::size_t bytes=3276800;
        if(argc==2&&std::strcmp(argv[1],"uncertain")==0) {
            auto * ops=new Ops;ops->failure=6;auto * reader=new MappedSourceReader(ops->files,*ops,scratch);
            reader->register_mapping(a,ops->files[0].bytes,10);reader->register_mapping(b,ops->files[1].bytes,11);
            rejected([&]{reader->upload_pair({a,b},model_read_alignment,[](unsigned,const void*){});});
            check(ops->reads==2&&ops->active==1&&!reader->stats().completed_windows,"Unknown helper was released or completed");
            rejected([&]{reader->upload_pair({a,b},model_read_alignment,[](unsigned,const void*){});});
            rejected([&]{ops->worker.stop_completed();});check(ops->reads==2,"Unknown read retried");
            std::cout<<"Actual timeout retained worker and backing; no retry\n"<<std::flush;std::_Exit(0);
        }
        {
            Ops ops;MappedSourceReader reader(ops.files,ops,scratch);reader.preflight_pipeline();
            reader.register_mapping(a,ops.files[0].bytes,10);reader.register_mapping(b,ops.files[1].bytes,11);
            ops.overlap=true;
            reader.upload_pair({a+123,b+34567},bytes,[&](unsigned i,const void * p){
                ops.consume(i,p,i?34567:123,bytes);
                check(reader.stats().completed_windows==2,"A live pair was published early");
            });
            ops.overlap=false;
            reader.upload_pair({a+3*model_read_window,b+3*model_read_window},1000,[&](unsigned i,const void * p){ops.consume(i,p,3*model_read_window,1000);});
            check(ops.peak==1&&ops.reads==6&&reader.stats().pipeline_batches==3&&reader.stats().completed_windows==6,"Pipeline accounting changed");
            check(reader.stats().worker_read_ns&&reader.stats().read_ns,"Pipeline timings missing");
            for(auto key:{a,b}){reader.before_unmap(key,ops.files[0].bytes);reader.after_unmap(key,ops.files[0].bytes);}reader.close_completed();check(ops.closes==2,"Descriptors leaked");
        }
        for(unsigned i=0;i<model_read_alignment;++i)check(scratch[-int(i)-1]==0xa5&&scratch[model_read_window+i]==0xa5,"8 MiB canary changed");
        for(int failure=0;failure<10;++failure) {
            Ops ops;MappedSourceReader reader(ops.files,ops,scratch);reader.register_mapping(a,ops.files[0].bytes,10);reader.register_mapping(b,ops.files[1].bytes,11);
            if(failure>=1&&failure<=5)ops.failure=failure;
            if(failure==6)ops.identity_changed=true;if(failure==7)ops.available=model_read_system_reserve;
            rejected([&]{
                if(failure==8)reader.upload_pair({a-1,b},bytes,[](unsigned,const void*){});
                else if(failure==9)reader.upload_pair({a,b},model_read_window/2,[](unsigned,const void*){});
                else reader.upload_pair({a+123,b+34567},bytes,[&](unsigned i,const void * p){ops.consume(i,p,i?34567:123,bytes);if(failure==0)reader.before_unmap(a,ops.files[0].bytes);});
            });
            const auto reads=ops.reads.load();rejected([&]{reader.upload_pair({a,b},bytes,[](unsigned,const void*){});});
            check(ops.reads==reads&&!reader.stats().completed_windows,"Failure retried or completion fabricated");
        }
        std::cout<<"One in-flight read, actual consumer overlap, exact bytes/EOF/canaries and failure retention passed\n";
    } catch(const std::exception & e){std::cerr<<e.what()<<'\n';return 1;}
}
