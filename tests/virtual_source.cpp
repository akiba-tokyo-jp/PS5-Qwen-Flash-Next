// SPDX-License-Identifier: MIT
#include "virtual_source.h"
#include <iostream>
using namespace qwen_app;
struct Ops final : VirtualSourceOps {
    std::uintptr_t at=1ull<<40;
    std::size_t span=0;
    unsigned reservations=0,queries=0,releases=0;
    std::uint32_t bits=0;
    bool bad_query=false,bad_span=false,bad_release=false;
    std::uintptr_t reserve(std::size_t bytes) override {++reservations;span=bytes;return at;}
    bool protection(std::uintptr_t p,std::uintptr_t & first,std::uintptr_t & last,std::uint32_t & protection) override {
        ++queries;first=p;last=p+span-(bad_span?1:0);protection=bits;return !bad_query;
    }
    bool release(std::uintptr_t p,std::size_t bytes) override {
        ++releases;if(p!=at||bytes!=span)throw std::runtime_error("Release range changed");return !bad_release;
    }
};
int main() {
    auto reject=[](auto action){try{action();}catch(const std::exception &){return;}throw std::runtime_error("Unsafe virtual source admitted");};
    for (const auto bytes : {std::uint64_t(16384),std::uint64_t(3508767456),std::uint64_t(102400491712)}) {
        Ops ops;const auto at=reserve_virtual_source(bytes,ops);release_virtual_source(at,bytes,ops);
        if(ops.reservations!=1||ops.queries!=1||ops.releases!=1||ops.span%16384||ops.span<bytes)return 1;
    }
    for(unsigned failure=0;failure<8;++failure) {
        Ops ops;
        if(failure==0)ops.at=0;
        if(failure==1)++ops.at;
        if(failure==2)ops.at=1ull<<47;
        if(failure==3)ops.bad_query=true;
        if(failure==4)ops.bad_span=true;
        if(failure==5)ops.bits=1;
        if(failure==6)ops.bits=2;
        if(failure==7)ops.bits=0x10;
        reject([&]{reserve_virtual_source(16384,ops);});if(ops.reservations!=1||ops.releases)return 1;
    }
    for(const auto bytes : {std::uint64_t(0),std::uint64_t((512ull<<30)+1)}) {
        Ops ops;reject([&]{reserve_virtual_source(bytes,ops);});if(ops.reservations||ops.queries||ops.releases)return 1;
    }
    Ops failed;const auto at=reserve_virtual_source(16384,failed);failed.bad_release=true;
    reject([&]{release_virtual_source(at,16384,failed);});if(failed.releases!=1)return 1;
    std::cout<<"Virtual source span, no-access protection, failure retention and single release checks passed; API stubs only\n";
}
