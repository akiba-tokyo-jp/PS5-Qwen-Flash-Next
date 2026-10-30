// SPDX-License-Identifier: MIT
#include "streaming_read_pool.h"
#include <cstring>
#include <iostream>
#include <vector>
int main(){try{
    constexpr std::size_t stride=2u<<20;std::vector<unsigned char>storage(4*stride+16384);
    const auto base=(reinterpret_cast<std::uintptr_t>(storage.data())+16383)&~std::uintptr_t(16383);
    std::array<void*,4>leases{};for(unsigned i=0;i<4;++i)leases[i]=reinterpret_cast<void*>(base+i*stride);
    std::array<qwen_app::BoundedReadRequest,12>requests{};for(unsigned i=0;i<12;++i)requests[i]={7,nullptr,16384,std::uint64_t(i)*16384};
    for(unsigned mode=0;mode<4;++mode){
        std::atomic<unsigned>active{0},reads{0},returns{0},callbacks{0};std::atomic<bool>first_done{false},refilled_before_first{false};
        qwen_app::StreamingReadPool pool([&](const qwen_app::BoundedReadRequest&r)->std::int64_t{
            ++active;++reads;const unsigned id=unsigned(r.offset/16384);if(id>=4&&!first_done)refilled_before_first=true;
            std::this_thread::sleep_for(std::chrono::milliseconds(id==0?20:2));std::memset(r.target,int(id),r.bytes);if(id==0)first_done=true;--active;++returns;
            return mode==1&&id==1?std::int64_t(r.bytes-1):std::int64_t(r.bytes);
        });pool.start();bool refused=false;
        try{pool.run(requests.data(),requests.size(),leases,[&](unsigned id){if(mode==3&&id==6)throw std::runtime_error("Expected admission refusal");},
            [&](unsigned id,const void*data,std::int64_t size){++callbacks;const auto*p=static_cast<const unsigned char*>(data);
                if(size!=16384||!std::all_of(p,p+size,[&](auto v){return v==id;}))throw std::runtime_error("Live payload was overwritten");
                if(mode==2&&id==1)throw std::runtime_error("Expected consumer refusal");});}
        catch(const std::runtime_error&){refused=true;}
        pool.require_completed();if(active||reads!=returns||pool.maximum_inflight()>4||refused!=(mode!=0))throw std::runtime_error("Failure did not drain positive read completions");
        if(!mode&&(callbacks!=12||reads!=12||!refilled_before_first))throw std::runtime_error("Completion did not refill before the slow first request");pool.stop_completed();
    }
    unsigned reads=0;qwen_app::StreamingReadPool invalid([&](const auto&r){++reads;return std::int64_t(r.bytes);});invalid.start();auto overlap=leases;overlap[1]=overlap[0];bool refused=false;
    try{invalid.run(requests.data(),1,overlap,[](unsigned){},[](unsigned,const void*,std::int64_t){});}catch(const std::invalid_argument&){refused=true;}
    if(!refused||reads)throw std::runtime_error("Overlapping leases started I/O");invalid.stop_completed();
    std::cout<<"PASS: actual refill, exact payloads, bounded four lanes, short read, consumer/admission failure drain, overlap refusal\n";return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
