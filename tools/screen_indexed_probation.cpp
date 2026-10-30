// SPDX-License-Identifier: MIT
// Replay actual closed routes; compare every replacement before host timing.
#include "indexed_probation_policy.h"
#include <chrono>
#include <iostream>
#include <sstream>
struct Route {unsigned layer;std::vector<std::int32_t>ids;};
struct Request {bool reset;std::vector<Route>routes;};
struct Result {std::uint64_t hits=0,misses=0,hash=1469598103934665603ull;};
template<class Policy>std::vector<Result>run(unsigned slots,const std::vector<Request>&requests,bool indexed){
    Policy policy;std::vector<std::int32_t>keys,locations(49*512,-1);std::vector<Result>results;
    for(const auto&request:requests){
        if(request.reset){policy.reset(49,512,slots,48);keys.assign(slots,-1);std::fill(locations.begin(),locations.end(),-1);}
        Result result;
        for(const auto&r:request.routes){
            policy.observe(r.layer,r.ids);for(auto id:r.ids)if(locations.at(r.layer*512+id)>=0)++result.hits;
            auto ids=r.ids;std::sort(ids.begin(),ids.end());
            for(auto id:ids){auto key=std::int32_t(r.layer*512+id);if(locations.at(key)>=0)continue;
                const auto slot=policy.victim(keys,r.layer,ids);if(slot<0)throw std::runtime_error("No eligible resident");
                if constexpr(std::is_same_v<Policy,qwen_app::IndexedProbationPolicy>)policy.replaced(slot,keys.at(slot),key);
                if(keys.at(slot)>=0)locations.at(keys[slot])=-1;keys[slot]=key;locations.at(key)=slot;++result.misses;
                result.hash=(result.hash^std::uint64_t(key))*1099511628211ull;
                result.hash=(result.hash^std::uint64_t(slot))*1099511628211ull;
            }
        }results.push_back(result);
    }return results;
}
int main(){try{
    unsigned slots,n;if(!(std::cin>>slots>>n)||!slots||n>16)return 2;std::vector<Request>requests;
    for(unsigned q=0;q<n;++q){unsigned reset,records;std::cin>>reset>>records;Request request{bool(reset),{}};
        for(unsigned i=0;i<records;++i){unsigned layer,count;std::cin>>layer>>count;Route r{layer,{}};std::set<std::int32_t>seen;
            for(unsigned k=0;k<count;++k){std::int32_t id;std::cin>>id;if(seen.insert(id).second)r.ids.push_back(id);}request.routes.push_back(std::move(r));}
        requests.push_back(std::move(request));}
    if(!std::cin||requests.empty()||!requests[0].reset)return 2;
    auto a=run<qwen_app::TemporalProbationPolicy>(slots,requests,false);auto b=run<qwen_app::IndexedProbationPolicy>(slots,requests,true);
    for(unsigned q=0;q<n;++q){if(std::tie(a[q].hits,a[q].misses,a[q].hash)!=std::tie(b[q].hits,b[q].misses,b[q].hash))throw std::runtime_error("Victim sequence changed");
        std::cout<<"COUNTS "<<q<<' '<<a[q].hits<<' '<<a[q].misses<<' '<<a[q].hash<<'\n';}
    for(unsigned round=0;round<4;++round)for(unsigned j=0;j<2;++j){const unsigned mode=(round%2)?1-j:j;
        const auto begin=std::chrono::steady_clock::now();if(mode)run<qwen_app::IndexedProbationPolicy>(slots,requests,true);else run<qwen_app::TemporalProbationPolicy>(slots,requests,false);
        const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count();std::cout<<"TIME "<<round<<' '<<mode<<' '<<ns<<'\n';}
    return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
