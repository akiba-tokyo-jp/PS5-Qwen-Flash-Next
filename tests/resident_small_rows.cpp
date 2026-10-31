// SPDX-License-Identifier: MIT
// Compile against the actual generated native source-reader header.
#include "resident-mapped-source.private.h"
#include "streaming_read_pool.h"
#include <iostream>
using namespace qwen_app;
static void check(bool ok){if(!ok)throw std::runtime_error("Small-row ownership control failed");}
struct Ops:SourceReadOps{
    std::array<SourceIdentity,3>ids{};std::atomic<unsigned>reads{0};
    Ops(){for(unsigned i=0;i<3;++i)ids[i]={1,i+1,0100444,1,1,32u<<20,1,0,1,0};}
    SourceIdentity identity(int fd)override{return ids.at(fd-1);}
    int open_direct(const std::string&p)override{return std::stoi(p)+1;}
    bool close_file(int)override{return true;}
    std::uint64_t system_headroom()override{return 512ull<<20;}
    std::int64_t read_at(int fd,void*target,std::size_t n,std::uint64_t offset)override{
        check(n%16384==0&&offset%16384==0&&offset+n<=ids.at(fd-1)[5]);++reads;
        for(std::size_t i=0;i<n;++i)static_cast<unsigned char*>(target)[i]=(offset+i+17u*(fd-1))%251;
        return n;
    }
};
int main()try{
    std::vector<unsigned char>storage(model_read_window+3*model_read_alignment,0xa5);
    auto*scratch=reinterpret_cast<unsigned char*>((reinterpret_cast<std::uintptr_t>(storage.data())+2*model_read_alignment-1)&~std::uintptr_t(model_read_alignment-1));
    for(const unsigned bytes:{320u,5120u}){
        Ops ops;std::vector<SourceFile>files;
        for(unsigned i=0;i<3;++i)files.push_back({std::to_string(i),ops.ids[i][5],ops.ids[i]});
        ResidentMappedSourceReader source(files,ops,scratch);constexpr std::uintptr_t base=0x1000000000;
        for(unsigned i=0;i<3;++i)source.register_mapping(base+i*0x100000000,ops.ids[i][5],i+1);
        StreamingReadPool pool([&](const BoundedReadRequest&r){return ops.read_at(r.fd,r.target,r.bytes,r.offset);});pool.start();
        std::array<std::uintptr_t,8>addresses{};std::array<unsigned,8>file{};
        for(unsigned i=0;i<8;++i){file[i]=i<4?0:i%3;
            addresses[i]=base+file[i]*0x100000000+(i<4?5u:(5u+2*i))*(1u<<20)+(i<4?320*i:17);}
        addresses[3]=addresses[0];
        std::array<std::uint64_t,5>stats{};unsigned seen=0;const auto owner=std::this_thread::get_id();
        const auto execute=[&](const std::array<SourceReadRequest,12>&rs,unsigned n,const std::array<void*,4>&leases,const std::function<void(unsigned)>&before,const std::function<void(unsigned,const void*,std::int64_t)>&use){
            std::array<BoundedReadRequest,12>jobs{};for(unsigned i=0;i<n;++i)jobs[i]={rs[i].fd,nullptr,rs[i].bytes,rs[i].offset};pool.run(jobs.data(),n,leases,before,use);
        };
        check(source.upload_small_rows(addresses,8,bytes,execute,[&](unsigned i,const void*p){
            check(i<8&&std::this_thread::get_id()==owner&&!(seen&(1u<<i))&&source.borrowed_window_contains(p,bytes));seen|=1u<<i;
            const auto at=addresses[i]-base-file[i]*0x100000000;
            for(unsigned j=0;j<bytes;++j)check(static_cast<const unsigned char*>(p)[j]==(at+j+17u*file[i])%251);
        },stats));
        check(seen==255&&ops.reads==5&&stats[0]==1&&stats[1]==8&&stats[2]==5&&stats[3]==8*bytes);
        check(source.stats().chunks==8&&source.stats().completed_windows==8&&source.stats().physical_read_calls==5);
        auto invalid=addresses;invalid[7]=base+ops.ids[0][5]-16;
        check(!source.upload_small_rows(invalid,8,bytes,execute,[](unsigned,const void*){},stats)&&ops.reads==5);
        pool.stop_completed();for(unsigned i=0;i<3;++i){source.before_unmap(base+i*0x100000000,ops.ids[i][5]);source.after_unmap(base+i*0x100000000,ops.ids[i][5]);}source.close_completed();
        for(unsigned i=0;i<model_read_alignment;++i)check(scratch[-int(i)-1]==0xa5&&scratch[model_read_window+i]==0xa5);
    }
    std::cout<<"PASS: exact320/5120-byte rows, duplicate/overlap merged,8 logical to5 physical reads, producer callbacks, EOF refusal and scratch canaries\n";
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
