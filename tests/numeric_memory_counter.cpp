// SPDX-License-Identifier: MIT
#include "numeric_memory_counter.h"
#include <iostream>
int main(){try{
    qwen_app::NumericMemoryCounter counter;unsigned resolves=0,reads=0;
    const auto resolve=[&](const char*,int*name,std::size_t*length){++resolves;name[0]=1;name[1]=7;*length=2;return 0;};
    const auto read=[&](const int*name,unsigned length,void*out,std::size_t*bytes){if(length!=2||name[0]!=1||name[1]!=7||*bytes!=4)throw std::runtime_error("Numeric name differs");*static_cast<std::uint32_t*>(out)=++reads;return 0;};
    if(counter.value("vm.free",resolve,read)!=1||counter.value("vm.free",resolve,read)!=2||resolves!=1||reads!=2)throw std::runtime_error("A memory value was cached");
    bool refused=false;try{counter.value("vm.free",resolve,[](const int*,unsigned,void*,std::size_t*){return -1;});}catch(const std::runtime_error&){refused=true;}
    if(!refused)throw std::runtime_error("Failed fresh observation was accepted");
    std::cout<<"PASS: numeric name resolved once, fresh values twice and failed observation refused\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
