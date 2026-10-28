// SPDX-License-Identifier: MIT
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace qwen_app {
struct LogitDifference {
    std::size_t columns=0,outside_tolerance=0;
    bool finite=true;
    double maximum=0,rms=0,p50=0,p95=0,p99=0,mean_shift=0,centered_rms=0,KL_reference_to_candidate=0;
    std::array<std::int32_t,5> reference_top{},candidate_top{};
    double reference_margin=0,candidate_margin=0;
};
// Caller owns the full-column scratch before entering any GPU epoch. No
// allocation, sampled vocabulary subset, or absolute-logit quality cutoff.
inline LogitDifference compare_logits(const float *candidate,const float *reference,std::size_t count,float *scratch) {
    LogitDifference out;out.columns=count;
    if(!candidate||!reference||!scratch||count<5||count>262144){out.finite=false;return out;}
    std::array<double,5> a_top,b_top;a_top.fill(-std::numeric_limits<double>::infinity());b_top=a_top;
    auto insert=[](double value,std::int32_t id,std::array<double,5>&values,std::array<std::int32_t,5>&ids){
        for(unsigned k=0;k<5;++k)if(value>values[k]){
            for(unsigned j=4;j>k;--j){values[j]=values[j-1];ids[j]=ids[j-1];}
            values[k]=value;ids[k]=id;break;
        }
    };
    double sum=0,squares=0;
    for(std::size_t i=0;i<count;++i){
        const double a=candidate[i],b=reference[i],delta=a-b,e=std::abs(delta);
        if(!std::isfinite(a)||!std::isfinite(b)){out.finite=false;return out;}
        scratch[i]=float(e);out.maximum=std::max(out.maximum,e);sum+=delta;squares+=delta*delta;
        out.outside_tolerance+=e>1e-5+1e-5*std::abs(b);
        insert(a,std::int32_t(i),a_top,out.candidate_top);insert(b,std::int32_t(i),b_top,out.reference_top);
    }
    out.mean_shift=sum/double(count);out.rms=std::sqrt(squares/double(count));
    out.centered_rms=std::sqrt(std::max(0.0,squares/double(count)-out.mean_shift*out.mean_shift));
    const auto percentile=[&](double fraction){const auto index=std::size_t(double(count-1)*fraction);
        std::nth_element(scratch,scratch+index,scratch+count);return double(scratch[index]);};
    out.p50=percentile(.50);out.p95=percentile(.95);out.p99=percentile(.99);
    out.reference_margin=b_top[0]-b_top[1];out.candidate_margin=a_top[0]-a_top[1];
    double za=0,zb=0;
    for(std::size_t i=0;i<count;++i){za+=std::exp(double(candidate[i])-a_top[0]);zb+=std::exp(double(reference[i])-b_top[0]);}
    const double logza=std::log(za)+a_top[0],logzb=std::log(zb)+b_top[0];
    for(std::size_t i=0;i<count;++i){const double probability=std::exp(double(reference[i])-logzb);
        out.KL_reference_to_candidate+=probability*((double(reference[i])-logzb)-(double(candidate[i])-logza));}
    out.KL_reference_to_candidate=std::max(0.0,out.KL_reference_to_candidate);
    return out;
}
}
