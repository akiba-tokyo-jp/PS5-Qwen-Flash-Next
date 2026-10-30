// SPDX-License-Identifier: MIT
#include "resident-mapped-source.private.h"
#include "completed_read_pool.h"
#include <iostream>
using namespace qwen_app;
static void check(bool b){if(!b)throw std::runtime_error("Completed source check failed");}
struct Ops:SourceReadOps{
    SourceIdentity id{1,2,0100444,0,0,32u<<20,1,0,1,0};std::atomic<unsigned>calls{0};
    SourceIdentity identity(int)override{return id;}int open_direct(const std::string&)override{return 1;}
    bool close_file(int)override{return true;}std::uint64_t system_headroom()override{return 512ull<<20;}
    std::int64_t read_at(int,void*p,std::size_t n,std::uint64_t offset)override{++calls;
        check(n<=(2u<<20)&&n%16384==0&&offset%16384==0&&offset+n<=id[5]);
        for(std::size_t i=0;i<n;++i)static_cast<unsigned char*>(p)[i]=(offset+i)%251;return n;}
};
int main(){try{
    std::vector<unsigned char>storage(model_read_window+16384);auto*scratch=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(storage.data())+16383)&~std::uintptr_t(16383));
    for(unsigned bytes:{537600u,460800u})for(bool ready:{false,true}){
        Ops ops;ResidentMappedSourceReader reader({{"weights",ops.id[5],ops.id}},ops,scratch);
        constexpr std::uintptr_t base=0x100000000;reader.register_mapping(base,ops.id[5],1);
        CompletedReadPool pool([&](const BoundedReadRequest&r){return ops.read_at(r.fd,r.target,r.bytes,r.offset);});pool.start();
        const auto producer=std::this_thread::get_id();
        const std::array<std::uintptr_t,4>at{base+(5u<<20)+17,base+(8u<<20)+131,base+(11u<<20)+7,base+(15u<<20)+511};unsigned consumed=0;
        const auto jobs=[](const std::array<SourceReadRequest,4>&r){std::array<BoundedReadRequest,4>j{};for(unsigned i=0;i<4;++i)j[i]={r[i].fd,r[i].target,r[i].bytes,r[i].offset};return j;};
        const auto perform=[&](const auto&r){return pool.read(jobs(r),4);};
        std::function<std::array<std::int64_t,4>(const std::array<SourceReadRequest,4>&,const std::function<void(unsigned,std::int64_t)>&)>completed;
        if(ready)completed=[&](const auto&r,const auto&consume){return pool.read_each(jobs(r),consume);};
        check(reader.upload_Q2_four(at,bytes,perform,[&](unsigned item,const void*p){check(std::this_thread::get_id()==producer);check(!(consumed&(1u<<item)));consumed|=1u<<item;
            for(unsigned i=0;i<bytes;++i)check(static_cast<const unsigned char*>(p)[i]==(at[item]-base+i)%251);},completed));
        const auto stats=reader.stats();check(consumed==15&&ops.calls==4&&stats.physical_read_calls==4&&stats.bytes==4ull*bytes&&stats.chunks==stats.completed_windows&&stats.consumer_ns&&stats.read_ns);
        const auto before=ops.calls.load();auto invalid=at;invalid[3]=base+ops.id[5]-16;
        check(!reader.upload_Q2_four(invalid,bytes,perform,[](unsigned,const void*){},completed));check(ops.calls==before);
        pool.require_completed();pool.stop_completed();reader.before_unmap(base,ops.id[5]);reader.after_unmap(base,ops.id[5]);reader.close_completed();
    }
    std::cout<<"Both Q2 formats and barrier/ready delivery preserve bytes, producer ownership, non-overlap and completed leases.\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
