// SPDX-License-Identifier: MIT
#include "resident-mapped-source.private.h"
#include "source_io_occupancy.h"
#include <iostream>
#include <thread>
using namespace qwen_app;
static void check(bool b){if(!b)throw std::runtime_error("Adjacent reader check failed");}
struct Ops:SourceReadOps{
    SourceIdentity id{1,2,0100444,0,0,10*1540096,1,0,1,0};
    unsigned calls=0;bool short_read=false;
    SourceIdentity identity(int)override{return id;}
    int open_direct(const std::string&)override{return 1;}
    bool close_file(int)override{return true;}
    std::uint64_t system_headroom()override{return 512ull<<20;}
    std::int64_t read_at(int,void*target,std::size_t n,std::uint64_t offset)override{
        check(n<=model_read_window&&n%16384==0&&offset%16384==0&&offset+n<=id[5]);++calls;
        for(std::size_t i=0;i<n;++i)static_cast<unsigned char*>(target)[i]=(offset+i)%251;
        return n-(short_read?1:0);
    }
};
int main(){try{
    std::vector<unsigned char>storage(model_read_window+16384);
    auto*scratch=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(storage.data())+16383)&~std::uintptr_t(16383));
    for(unsigned count=1;count<=5;++count){Ops ops;ResidentMappedSourceReader reader({{"weights",ops.id[5],ops.id}},ops,scratch);
        const auto before=reader.stats();unsigned callbacks=0;
        reader.upload_Q2_bundle_group(1,ops.id,1540096,count,[&](unsigned item,unsigned role,const void*p,std::size_t n){
            check(item<count&&role<3&&n==(role==2?460800:537600));
            const auto offset=(item+1)*1540096ull+(role==0?0:role==1?537600:1075200);
            for(std::size_t i=0;i<n;++i)check(static_cast<const unsigned char*>(p)[i]==(offset+i)%251);++callbacks;});
        const auto after=reader.stats();check(ops.calls==1&&callbacks==3*count&&after.physical_read_calls-before.physical_read_calls==1&&after.physical_read_bytes-before.physical_read_bytes==count*1540096ull);
        reader.close_completed();
    }
    for(unsigned invalid=0;invalid<4;++invalid){Ops ops;ResidentMappedSourceReader reader({{"weights",ops.id[5],ops.id}},ops,scratch);bool refused=false;
        if(invalid==3)ops.short_read=true;
        try{reader.upload_Q2_bundle_group(1,ops.id,invalid==2?ops.id[5]:0,invalid==0?0:invalid==1?6:1,[](unsigned,unsigned,const void*,std::size_t){});}catch(const std::exception&){refused=true;}
        check(refused);
    }
    SourceIOOccupancy occupancy;occupancy.begin();std::thread worker([&]{occupancy.begin();occupancy.end();});worker.join();occupancy.end();
    const auto s=occupancy.snapshot();check(s[0]==2&&s[1]==1&&s[4]>0&&s[5]==2&&s[6]==0);
    check(sizeof(SourceIOOccupancy)<=128);
    std::cout<<"Exact bytes for 1..5 Experts, one read, invalid groups, short reads and two-lane occupancy passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
