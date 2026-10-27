// SPDX-License-Identifier: MIT
#pragma once
#include "expert_verification_cost.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
namespace qwen_app {
using SingleTokenExpertRoutes=std::array<std::uint16_t,480>;
class OnlineExpertVerification {
    struct Observation {int token=-1;SingleTokenExpertRoutes routes{};std::uint64_t at=0;};
    std::array<Observation,32> observations_{};
    std::uint64_t tick_=0,samples_=0,attempts_=0,accepted_=0;
    double ordinary_=0,source_=0,capture_=0,restore_=0;
    const Observation *find(int token)const {
        for(const auto &e:observations_)if(e.token==token)return &e;
        return nullptr;
    }
public:
    void observe(int token,const SingleTokenExpertRoutes &routes,double seconds,double source_seconds) {
        if(token<0||token>=262144||!std::isfinite(seconds)||seconds<=0||
           !std::isfinite(source_seconds)||source_seconds<0||source_seconds>seconds)
            throw std::invalid_argument("Online verification requires finite completed timing observations");
        for(unsigned l=0;l<48;++l)for(unsigned i=0;i<10;++i) {
            if(routes[l*10+i]>=512)throw std::invalid_argument("Online route ID exceeds the original model");
            for(unsigned j=0;j<i;++j)if(routes[l*10+i]==routes[l*10+j])
                throw std::invalid_argument("Online single-token routes require distinct actual Experts");
        }
        auto it=std::find_if(observations_.begin(),observations_.end(),[&](const Observation &o){return o.token==token;});
        if(it==observations_.end())it=std::min_element(observations_.begin(),observations_.end(),
            [](const Observation &a,const Observation &b){return a.at<b.at;});
        *it={token,routes,++tick_};
        if(!samples_){ordinary_=seconds;source_=source_seconds;}
        else {ordinary_=(3*ordinary_+seconds)/4;source_=(3*source_+source_seconds)/4;}
        ++samples_;
    }
    unsigned choose(int pending,int draft)const {
        const auto *a=find(pending),*b=find(draft);
        if(!samples_||!a||!b)return 1;
        // One causally eligible calibration attempt. Its success is not a
        // calibrated acceptance probability or a native speed qualification.
        if(!attempts_)return 2;
        unsigned unique=480;
        for(unsigned l=0;l<48;++l)for(unsigned i=0;i<10;++i)
            if(std::find(a->routes.begin()+l*10,a->routes.begin()+(l+1)*10,b->routes[l*10+i])==a->routes.begin()+(l+1)*10)++unique;
        const double acceptance=double(accepted_+1)/double(attempts_+2);
        // Historical routes approximate future unions. Include measured
        // checkpoint costs and expected ordinary work after full rejection.
        // Before a rejection supplies a restore measurement, charge capture
        // time as a provisional restore estimate rather than assuming zero.
        // This proxy is not a physical bound or an adoption qualification.
        const auto restore_estimate=restore_>0?restore_:capture_;
        const auto candidate=capture_+2*(ordinary_-source_)+source_*double(unique)/480+
            (1-acceptance)*(restore_estimate+ordinary_);
        const std::array<ExpertVerificationCost,3> costs{{
            {1,1,ordinary_,true},{2,1+acceptance,candidate,true},{4,1,ordinary_,false}}};
        return choose_expert_verification_width(costs);
    }
    void verified(bool accepted,double capture,double restore) {
        if(!std::isfinite(capture)||capture<0||!std::isfinite(restore)||restore<0)
            throw std::invalid_argument("Online checkpoint costs must be complete and finite");
        capture_=attempts_?(3*capture_+capture)/4:capture;
        if(!accepted)restore_=restore;
        ++attempts_;accepted_+=accepted;
    }
};
struct ExpertVerificationHooks {
    std::function<void()> before_process;
    std::function<void(int,std::uint64_t)> completed_ordinary;
    std::function<unsigned(int,int)> choose;
    std::function<void(bool,double,double)> verified;
};
}
