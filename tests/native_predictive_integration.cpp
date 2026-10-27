// SPDX-License-Identifier: MIT
// Real native policy/source coordinator; synthetic bytes and no learned model.
#include "mapped_source.h"
#include "cross_layer_forecast.h"
#include "online_expert_verification.h"
#include <atomic>
#include <cstdlib>
#include <malloc.h>
#include <iostream>
#include <map>
using namespace qwen_app;
static void check(bool v){if(!v)throw std::runtime_error("Native predictive integration control failed");}
template<class F>static void refused(F f){bool r=false;try{f();}catch(const std::exception&){r=true;}check(r);}
struct Ops final:SourceReadOps {
    std::vector<SourceFile> files;std::map<int,unsigned> descriptors;
    std::mutex mutex;std::condition_variable changed;
    bool hold=false,entered=false,release=false,short_read=false;
    unsigned opens=0,reads=0;
    Ops(){for(unsigned i=0;i<3;++i){const auto bytes=(16ull<<20)-(i==2?7000:0);
        files.push_back({"original-"+std::to_string(i),bytes,{1,i+1,0100644,1,1,bytes,10,0,10,0}});descriptors[10+i]=i;}}
    SourceIdentity identity(int fd)override{return files.at(descriptors.at(fd)).identity;}
    int open_direct(const std::string &path)override{
        for(unsigned i=0;i<3;++i)if(files[i].path==path){int fd=100+int(++opens);descriptors[fd]=i;return fd;}return -1;
    }
    bool close_file(int fd)override{descriptors.erase(fd);return true;}
    std::uint64_t system_headroom()override{return 512ull<<20;}
    std::int64_t read_at(int fd,void *target,std::size_t bytes,std::uint64_t offset)override{
        const auto i=descriptors.at(fd);check(offset+bytes<=files[i].bytes&&bytes==padded_bank_stride);
        {std::unique_lock<std::mutex> lock(mutex);++reads;entered=true;changed.notify_all();if(hold)changed.wait(lock,[&]{return release;});}
        std::memset(target,19+int(i),bytes);return std::int64_t(bytes)-(short_read?1:0);
    }
};
static std::shared_ptr<void> allocate(std::size_t bytes){
    auto *p=_aligned_malloc(bytes,16384);check(p);
    return {p,_aligned_free};
}
int main(int argc,char **argv){try {
    const std::string mode=argc==2?argv[1]:"positive";
    if(mode=="timeout") {
        ExpertPrefetchIO worker;std::mutex mutex;std::condition_variable changed;bool release=false,finished=false;
        auto allocation=allocate(16384);std::weak_ptr<void> retained=allocation;
        worker.submit([&,allocation]{std::unique_lock<std::mutex> lock(mutex);changed.wait(lock,[&]{return release;});
            finished=true;changed.notify_all();});
        allocation.reset();refused([&]{worker.complete(std::chrono::milliseconds(2));});check(!retained.expired());
        refused([&]{worker.submit([]{});});
        {std::lock_guard<std::mutex> lock(mutex);release=true;changed.notify_all();}
        refused([&]{worker.complete();});check(!retained.expired());
        {std::unique_lock<std::mutex> lock(mutex);check(changed.wait_for(lock,std::chrono::seconds(1),[&]{return finished;}));}
        std::cout<<"{\"timeout_retains_job_and_actual_lease\":true,\"PS5_operations\":0}\n";return 0;
    }
    CrossLayerForecast forecast;std::array<int,10> a{},b{};
    for(unsigned i=0;i<10;++i){a[i]=int(i);b[i]=40+int(i);}
    forecast.observe(0,1,a.data(),10);check(forecast.predict(1,{})==-1);
    forecast.observe(1,1,b.data(),10);
    forecast.observe(0,1,a.data(),10);check(forecast.predict(1,{})==-1);
    forecast.observe(1,1,b.data(),10);forecast.observe(0,1,a.data(),10);
    check(forecast.predict(1,{})==40&&forecast.predict(1,{512+40})==41);
    std::array<int,20> batched{};std::copy(a.begin(),a.end(),batched.begin());
    std::copy(a.begin(),a.end(),batched.begin()+10);
    forecast.observe(2,2,batched.data(),20);check(forecast.predict(3,{})==-1);
    auto bad=a;bad[9]=bad[0];refused([&]{forecast.observe(0,1,bad.data(),10);});
    SingleTokenExpertRoutes routes{},other{};
    for(unsigned l=0;l<48;++l)for(unsigned i=0;i<10;++i){routes[l*10+i]=i;other[l*10+i]=100+i;}
    OnlineExpertVerification planner;check(planner.choose(1,2)==1);
    planner.observe(1,routes,1,.95);planner.observe(2,routes,1,.95);check(planner.choose(1,2)==2);
    planner.verified(true,.01,0);check(planner.choose(1,2)==2);
    planner.observe(2,other,1,.95);check(planner.choose(1,2)==1);
    planner.observe(2,routes,1,.95);planner.verified(false,10,10);check(planner.choose(1,2)==1);
    refused([&]{planner.observe(1,routes,1,2);});
    Ops ops;auto scratch=allocate(model_read_window);
    MappedSourceReader reader(ops.files,ops,scratch.get());
    constexpr std::uintptr_t base=1ull<<40;
    for(unsigned i=0;i<3;++i)reader.register_mapping(base+(i*(32ull<<20)),ops.files[i].bytes,10+int(i));
    reader.enable_source_schedule();
    std::array<ExpertPrefetchDestination,3> banks{};
    std::array<std::uintptr_t,3> sources{};std::array<std::size_t,3> residues{{256,256,256}};
    const auto geometry=selected_padded_cache_geometry();
    for(unsigned i=0;i<3;++i){auto allocation=allocate(geometry.tensor_bytes());
        banks[i]={allocation.get(),geometry.tensor_bytes(),256,allocation};
        sources[i]=base+i*(32ull<<20)+256;
        std::memset(banks[i].data,0xa5,2*padded_bank_stride);}
    // Ineligible envelopes start no I/O and preserve the current slot.
    auto crossing=sources;crossing[2]+=(16ull<<20)-bank_expert_bytes-16384;
    check(!reader.begin_expert_prefetch(crossing,banks,1,residues)&&ops.reads==0);
    ops.hold=true;ops.short_read=mode=="short";
    check(reader.begin_expert_prefetch(sources,banks,1,residues));
    {std::unique_lock<std::mutex> lock(ops.mutex);check(ops.changed.wait_for(lock,std::chrono::seconds(1),[&]{return ops.entered;}));}
    for(const auto &bank:banks)for(unsigned i=0;i<16384;++i)check(static_cast<unsigned char *>(bank.data)[i]==0xa5);
    // Only the worker can advance before this explicitly released completion.
    {std::lock_guard<std::mutex> lock(ops.mutex);check(ops.reads==1);ops.release=true;ops.changed.notify_all();}
    if(mode=="short") {
        refused([&]{reader.complete_expert_prefetch();});refused([&]{reader.close_completed();});
        check(reader.stats().predictive_experts==0);
    }else {
        reader.require_completed_window();check(ops.reads==3);
        check(reader.stats().predictive_experts==1&&reader.stats().physical_read_calls==3&&
            reader.stats().physical_read_bytes==3*padded_bank_stride);
        for(unsigned role=0;role<3;++role){auto *p=static_cast<unsigned char *>(banks[role].data);
            for(std::size_t i=0;i<padded_bank_stride;++i)check(p[i]==0xa5&&p[padded_bank_stride+i]==19+role);}
        for(unsigned i=0;i<3;++i){const auto address=base+i*(32ull<<20);
            reader.before_unmap(address,ops.files[i].bytes);reader.after_unmap(address,ops.files[i].bytes);}
        reader.close_completed();
    }
    std::cout<<"{\"actual_source_coordinator\":true,\"forecast_and_online_cost\":true,\"passed\":true,\"PS5_operations\":0}\n";
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
