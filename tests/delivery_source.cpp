// SPDX-License-Identifier: MIT
// Compile against the exact generated native source-reader header.
#include "resident-mapped-source.private.h"
#include "delivery_read_pool.h"
#include <iostream>
using namespace qwen_app;
static void check(bool ok){if(!ok)throw std::runtime_error("Streaming source ownership check failed");}
struct Ops:SourceReadOps{
    std::array<SourceIdentity,3>ids{};std::atomic<unsigned>reads{0};
    Ops(){for(unsigned i=0;i<3;++i)ids[i]={1,i+1,0100444,1,1,32u<<20,1,0,1,0};}
    SourceIdentity identity(int fd)override{return ids.at(fd-1);}
    int open_direct(const std::string&p)override{return std::stoi(p)+1;}
    bool close_file(int)override{return true;}
    std::uint64_t system_headroom()override{return 512ull<<20;}
    std::int64_t read_at(int fd,void*target,std::size_t n,std::uint64_t offset)override{
        check(n%16384==0&&offset%16384==0&&offset+n<=ids.at(fd-1)[5]);++reads;
        for(std::size_t i=0;i<n;++i)static_cast<unsigned char*>(target)[i]=(offset+i+17u*(fd-1))%251;return n;
    }
};
int main(){try{
    std::vector<unsigned char>storage(model_read_window+3*model_read_alignment,0xa5);
    auto*scratch=reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(storage.data())+2*model_read_alignment-1)&~std::uintptr_t(model_read_alignment-1));
    for(unsigned experts=1;experts<=4;++experts){
        Ops ops;std::vector<SourceFile>files;for(unsigned i=0;i<3;++i)files.push_back({std::to_string(i),ops.ids[i][5],ops.ids[i]});
        ResidentMappedSourceReader source(files,ops,scratch);constexpr std::uintptr_t base=0x1000000000;
        for(unsigned i=0;i<3;++i)source.register_mapping(base+i*0x100000000,ops.ids[i][5],i+1);
        DeliveryReadPool pool([&](const BoundedReadRequest&r){return ops.read_at(r.fd,r.target,r.bytes,r.offset);});pool.start();
        std::array<std::uintptr_t,12>addresses{};std::array<std::size_t,12>sizes{};const unsigned count=experts*3;
        for(unsigned e=0;e<experts;++e)for(unsigned role=0;role<3;++role){const unsigned i=e*3+role;addresses[i]=base+role*0x100000000+(5u+e*2)*(1u<<20)+17;sizes[i]=role==2?460800:537600;}
        const auto producer=std::this_thread::get_id();unsigned seen=0;
        const auto execute=[&](const std::array<SourceReadRequest,12>&rs,unsigned n,const std::array<void*,4>&leases,const std::function<void(unsigned)>&before,const std::function<void(unsigned,const void*,std::int64_t)>&use){
            std::array<BoundedReadRequest,12>jobs{};for(unsigned i=0;i<n;++i)jobs[i]={rs[i].fd,nullptr,rs[i].bytes,rs[i].offset};pool.run(jobs.data(),n,leases,before,use);
        };
        check(source.upload_Q2_stream(addresses,sizes,count,execute,[&](unsigned i,const void*p){
            check(std::this_thread::get_id()==producer&&i<count&&!(seen&(1u<<i))&&source.borrowed_window_contains(p,sizes[i]));seen|=1u<<i;
            const auto offset=addresses[i]-base-(i%3)*0x100000000;for(unsigned j=0;j<sizes[i];++j)check(static_cast<const unsigned char*>(p)[j]==(offset+j+17u*(i%3))%251);
        }));
        check(seen==((1u<<count)-1)&&ops.reads==count&&source.stats().physical_read_calls==count&&source.stats().chunks==count&&source.stats().completed_windows==count);
        auto invalid=addresses;invalid[count-1]=base+((count-1)%3)*0x100000000+ops.ids[0][5]-16;const auto previous=ops.reads.load();
        check(!source.upload_Q2_stream(invalid,sizes,count,execute,[](unsigned,const void*){})&&ops.reads==previous);
        pool.stop_completed();for(unsigned i=0;i<3;++i){source.before_unmap(base+i*0x100000000,ops.ids[i][5]);source.after_unmap(base+i*0x100000000,ops.ids[i][5]);}source.close_completed();
        for(unsigned i=0;i<model_read_alignment;++i)check(scratch[-int(i)-1]==0xa5&&scratch[model_read_window+i]==0xa5);
    }

    {
        Ops ops;std::vector<SourceFile>files;for(unsigned i=0;i<3;++i)files.push_back({std::to_string(i),ops.ids[i][5],ops.ids[i]});
        ResidentMappedSourceReader source(files,ops,scratch);constexpr std::uintptr_t base=0x1000000000;
        for(unsigned i=0;i<3;++i)source.register_mapping(base+i*0x100000000,ops.ids[i][5],i+1);
        DeliveryReadPool pool([&](const BoundedReadRequest&r){return ops.read_at(r.fd,r.target,r.bytes,r.offset);});pool.start();
        const auto producer=std::this_thread::get_id();
        const auto execute=[&](const auto&rs,unsigned n,const auto&leases,const auto&before,const auto&use){std::array<BoundedReadRequest,960>jobs{};for(unsigned i=0;i<n;++i)jobs[i]={rs[i].fd,nullptr,rs[i].bytes,rs[i].offset};pool.run(jobs.data(),n,leases,before,use);};
        std::array<SourceReadRequest,4>bundles{};std::array<SourceIdentity,4>identity{};unsigned callbacks=0;
        for(unsigned i=0;i<4;++i){bundles[i]={1,nullptr,1540096,(8u+2*i)*(1u<<20)};identity[i]=ops.ids[0];}
        check(source.upload_delivery_bundles(bundles,identity,4,execute,[&](unsigned i,unsigned role,const void*p,std::size_t bytes){check(std::this_thread::get_id()==producer&&i<4&&role<3&&bytes==(role==2?460800:537600));const auto offset=bundles[i].offset+role*537600;for(unsigned j=0;j<bytes;++j)check(static_cast<const unsigned char*>(p)[j]==(offset+j)%251);++callbacks;}));
        check(callbacks==12);auto invalid=bundles;invalid[3].offset=ops.ids[0][5]-16384;const auto before=ops.reads.load();check(!source.upload_delivery_bundles(invalid,identity,4,execute,[](unsigned,unsigned,const void*,std::size_t){})&&ops.reads==before);
        std::array<std::uintptr_t,960>addresses{};std::array<std::size_t,960>sizes{};std::array<bool,60>seen{};
        for(unsigned e=0;e<20;++e)for(unsigned role=0;role<3;++role){const unsigned i=e*3+role;addresses[i]=base+role*0x100000000+(5u+e)*(1u<<20)+17;sizes[i]=role==2?460800:537600;}
        check(source.upload_delivery_wide(addresses,sizes,60,execute,[&](unsigned i,const void*p){check(std::this_thread::get_id()==producer&&i<60&&!seen[i]);seen[i]=true;const auto offset=addresses[i]-base-(i%3)*0x100000000;for(unsigned j=0;j<sizes[i];++j)check(static_cast<const unsigned char*>(p)[j]==(offset+j+17u*(i%3))%251);})==20);
        check(std::all_of(seen.begin(),seen.end(),[](bool v){return v;}));pool.stop_completed();
        for(unsigned i=0;i<3;++i){source.before_unmap(base+i*0x100000000,ops.ids[i][5]);source.after_unmap(base+i*0x100000000,ops.ids[i][5]);}source.close_completed();
        for(unsigned i=0;i<model_read_alignment;++i)check(scratch[-int(i)-1]==0xa5&&scratch[model_read_window+i]==0xa5);
    }
    std::cout<<"PASS: exact compiled source, three mixed-size projections,1..4 Experts plus four bundles and60-read queue, producer-only callbacks,8MiB canaries, EOF refusal before I/O\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
