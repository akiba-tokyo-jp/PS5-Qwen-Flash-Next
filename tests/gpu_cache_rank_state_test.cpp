// SPDX-License-Identifier: MIT
#include "gpu_cache_rank_state.h"
#include "expert_routing_experiment.h"
#include <cassert>
#include <cstdio>
#include <cstring>

int main(){
    qwen_app::GpuCacheRankSnapshot state;std::array<float,512>coefficients{},source{},expected{};
    std::array<unsigned char,512>resident{};
    bool caught=false;try{state.coefficients(0,coefficients.data(),512);}catch(const std::invalid_argument&){caught=true;}assert(caught);
    for(unsigned pattern=0;pattern<4;++pattern){
        state.reset();
        for(unsigned i=0;i<512;++i){resident[i]=pattern==1||(pattern==2&&i%2)||(pattern==3&&(i==0||i==511));
            state.resident(17,i,resident[i]);source[i]=float(i)/1024.0f;}
        state.latch();state.coefficients(17,coefficients.data(),512);
        qwen_app::cache_rank_scores(source.data(),expected.data(),resident.data(),512,1.5f);
        for(unsigned row=0;row<2;++row)for(unsigned i=0;i<512;++i){const float actual=source[i]*coefficients[i];assert(!std::memcmp(&actual,&expected[i],4));}
        const auto latched=coefficients;state.resident(17,0,!resident[0]);state.coefficients(17,coefficients.data(),512);assert(coefficients==latched);
        state.latch();state.coefficients(17,coefficients.data(),512);assert(coefficients[0]!=latched[0]);
    }
    caught=false;try{state.resident(49,0,true);}catch(const std::invalid_argument&){caught=true;}assert(caught);
    caught=false;try{state.resident(0,512,true);}catch(const std::invalid_argument&){caught=true;}assert(caught);
    caught=false;try{state.coefficients(48,coefficients.data(),512);}catch(const std::invalid_argument&){caught=true;}assert(caught);
    caught=false;try{state.coefficients(0,coefficients.data(),511);}catch(const std::invalid_argument&){caught=true;}assert(caught);
    std::array<float,48*512>matrix{};state.reset();
    caught=false;try{state.coefficients_all(matrix.data(),matrix.size());}catch(const std::invalid_argument&){caught=true;}assert(caught);
    for(unsigned layer=0;layer<48;++layer)for(unsigned i=0;i<512;++i)state.resident(layer,i,(layer*3+i)%7==0);
    state.latch();state.coefficients_all(matrix.data(),matrix.size());
    for(unsigned layer=0;layer<48;++layer){
        state.coefficients(layer,coefficients.data(),coefficients.size());
        for(unsigned i=0;i<512;++i){assert(matrix[layer*512+i]==((layer*3+i)%7==0?1.5f:1.0f));assert(matrix[layer*512+i]==coefficients[i]);}
    }
    state.resident(0,0,false);state.coefficients_all(matrix.data(),matrix.size());assert(matrix[0]==1.5f);
    state.latch();state.coefficients_all(matrix.data(),matrix.size());assert(matrix[0]==1.0f);
    caught=false;try{state.coefficients_all(matrix.data(),matrix.size()-1);}catch(const std::invalid_argument&){caught=true;}assert(caught);
    caught=false;try{state.coefficients_all(nullptr,matrix.size());}catch(const std::invalid_argument&){caught=true;}assert(caught);
    std::puts("Latched masks, the complete 48-layer coefficient matrix, two rows and malformed geometry controls passed.");
}
