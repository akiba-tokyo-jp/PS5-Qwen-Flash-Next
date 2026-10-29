// SPDX-License-Identifier: MIT
#include "expert_routing_experiment.h"
#include <cassert>
#include <limits>
int main(){
    std::array<float,512>a{},b{};std::array<unsigned char,512>resident{};
    for(unsigned i=0;i<512;++i)a[i]=float(i+1)/1000;
    resident[300]=1;qwen_app::cache_rank_scores(a.data(),b.data(),resident.data(),512,1.5f);
    assert(b[300]>a[400]&&b[400]==a[400]&&a[300]==.301f);
    qwen_app::cache_rank_scores(a.data(),b.data(),resident.data(),512,1);assert(a==b);
    for(unsigned m=0;m<5;++m){assert(qwen_app::experimental_expert_count(m,4)==10);assert(qwen_app::experimental_expert_count(m,2)==10);}
    assert(qwen_app::experimental_expert_count(2,1)==8&&qwen_app::experimental_expert_count(3,1)==6);
    assert(qwen_app::bounded_expert_aggregate(10,8)==8&&qwen_app::bounded_expert_aggregate(10,6)==6);
    assert(qwen_app::bounded_expert_aggregate(10,10)==10&&qwen_app::bounded_expert_aggregate(6,10)==6);
    a[42]=std::numeric_limits<float>::quiet_NaN();bool refused=false;
    try{qwen_app::cache_rank_scores(a.data(),b.data(),resident.data(),512,1.5f);}catch(const std::exception&){refused=true;}assert(refused);
}
