// SPDX-License-Identifier: MIT
// Compile against the generated experimental header, not the selected default.
#include "mapped_copy.h"
#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <vector>
static void check(bool value,const char*m){if(!value)throw std::runtime_error(m);}
int main(){try{
    using namespace qwen_app;configure_mapped_copy(true);set_mapped_copy_scope(true);
    const std::array<std::size_t,6>sizes{(256u<<10)-1,256u<<10,460800,537600,1u<<20,1540096};
    std::vector<unsigned char>source((2u<<20)+128),target(source.size());
    for(std::size_t i=0;i<source.size();++i)source[i]=static_cast<unsigned char>(i*131+71);
    unsigned calls=0;
    for(auto threshold:{1u<<20,256u<<10}){
        Q2_copy_minimum_bytes.store(threshold);
        for(auto size:sizes)for(auto offset:{0u,1u,31u,63u,64u}){
            std::fill(target.begin(),target.end(),0xa5);const auto before=mapped_copy_stats();
            const bool done=try_streaming_mapped_copy(target.data()+offset,source.data()+offset,size);
            check(done==(size>=threshold),"Threshold dispatch differs");
            if(done){++calls;check(!std::memcmp(target.data()+offset,source.data()+offset,size),"Copied quantized bytes differ");}
            else check(std::all_of(target.begin(),target.end(),[](auto x){return x==0xa5;}),"Rejected copy wrote destination");
            check(std::all_of(target.begin(),target.begin()+offset,[](auto x){return x==0xa5;})&&
                  std::all_of(target.begin()+offset+size,target.end(),[](auto x){return x==0xa5;}),"Copy escaped destination bounds");
            const auto after=mapped_copy_stats();check(after.calls-before.calls==unsigned(done)&&after.bytes-before.bytes==(done?size:0),"Copy observer counters differ");
        }
    }
    Q2_copy_minimum_bytes.store(256u<<10);
    check(!try_streaming_mapped_copy(source.data()+1,source.data(),460800),"Overlapping source admitted");
    check(!try_streaming_mapped_copy(reinterpret_cast<void*>(UINTPTR_MAX-10),source.data(),460800),"Overflow destination admitted");
    check(!try_streaming_mapped_copy(target.data(),nullptr,460800),"Null source admitted");
    set_mapped_copy_scope(false);check(!try_streaming_mapped_copy(target.data(),source.data(),460800),"Inactive copy scope admitted");
    std::cout<<"Compressed-size threshold dispatch, "<<calls<<" byte-exact copies, canaries, overlap/overflow and counters passed\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
