// SPDX-License-Identifier: MIT
#include "immutable_row_cache.h"
#include "streaming_read_pool.h"
#include "decode_prefill_protection.h"
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <memory>
#include <vector>
using namespace qwen_app;
void need(bool v){if(!v)throw std::runtime_error("Speed follow-up invariant failed");}
int main()try{
    DecodePrefillProtection history;history.begin(true,true);history.observe(0,{7,8},true);history.commit();history.observe(0,{9},true);
    history.begin(true,false);need((*history.keys(false))[7]&&(*history.keys(false))[8]&&!(*history.keys(false))[9]&&!history.keys(true));
    history.begin(false,true);need(!history.keys(false));
    auto cache=std::make_unique<ImmutableRowCache>();std::array<unsigned char,5120>data{};data.fill(0xa7);
    need(!cache->get(1,0,320));cache->put(1,0,320,data.data());data.fill(0x19);
    need(static_cast<const unsigned char*>(cache->get(1,0,320))[0]==0xa7&&reinterpret_cast<std::uintptr_t>(cache->get(1,0,320))%16==0);
    need(!cache->get(2,0,320)&&!cache->get(1,320,320)&&!cache->get(1,0,5120));
    cache->put(1,0,5120,data.data());need(!std::memcmp(cache->get(1,0,5120),data.data(),5120));
    for(unsigned i=0;i<1025;++i)cache->put(3,i*320,320,data.data());
    need(!cache->get(3,0,320)&&cache->get(3,1024*320,320));cache->clear();need(!cache->get(3,320,320));
    std::vector<unsigned char>storage((8u<<20)+16384);auto*memory=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(storage.data())+16383)&~std::uintptr_t(16383));std::array<void*,4>leases{};
    for(unsigned i=0;i<4;++i)leases[i]=static_cast<unsigned char*>(memory)+i*(2u<<20);
    std::array<BoundedReadRequest,12>jobs{};for(unsigned i=0;i<12;++i)jobs[i]={1,nullptr,16384,i*16384ULL};
    for(unsigned mode=0;mode<4;++mode){StreamingReadPool pool([&](const BoundedReadRequest&r)->std::int64_t{
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
            if(mode==2&&r.offset==0)throw std::runtime_error("Injected read error");
            std::memset(r.target,int(r.offset/16384),r.bytes);return mode==1&&r.offset==0?0:std::int64_t(r.bytes);});pool.start();
        unsigned consumed=0;bool failed=false;try{pool.run(jobs.data(),12,leases,[](unsigned){},[&](unsigned id,const void*p,std::int64_t){
            if(mode==3&&id==0)throw std::runtime_error("Injected consumer error");
            need(static_cast<const unsigned char*>(p)[0]==id);++consumed;});}catch(...){failed=true;}
        pool.require_completed();const auto s=pool.delivery_timing();need(s[1]==s[2]&&s[0]==1);
        need(std::accumulate(s.begin()+8,s.begin()+13,std::uint64_t(0))==s[7]);
        if(!mode)need(!failed&&consumed==12&&s[1]==12&&s[13]==0&&pool.maximum_inflight()>1);
        else need(failed&&s[15]==1);pool.stop_completed();
    }
    std::cout<<"PASS: owned row bytes, file/offset/size isolation, eviction/reset, four-lane accounting and drained failures; row-cache allocation="<<sizeof(ImmutableRowCache)<<" bytes\n";
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
