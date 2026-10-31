// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include "expert_gate_up_fixture_assets.private.h"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <vector>
extern "C" void qwen_app_gate_up_trial_select(bool);
extern "C" std::uint64_t qwen_app_gate_up_trial_selections();
namespace qwen_app {void verify_native_startup_file_direct(const std::string&,std::uint64_t,const std::string&,unsigned);}
namespace qwen_app {namespace gate_up_fixture {
using Json=nlohmann::json;using Clock=std::chrono::steady_clock;
inline void need(bool v,const char*m){if(!v)throw std::runtime_error(m);}
inline float decoded(const unsigned char*p,unsigned i){
    p+=(i/256)*84;const unsigned j=i%256,s=p[j/16],q=(p[16+(j/128)*32+j%32]>>(2*((j%128)/32)))&3;
    ggml_fp16_t d,dm;std::memcpy(&d,p+80,2);std::memcpy(&dm,p+82,2);
    return(ggml_fp16_to_fp32(d)*float(s&15))*float(q)-ggml_fp16_to_fp32(dm)*float(s>>4);
}
inline Json run(void(*checkpoint)(),void(*stage)(const char*),void(*admit)()){
    verify_native_startup_file_direct(gate_up_pack_path,gate_up_pack_bytes,gate_up_pack_sha256,60);
    const int fd=open(gate_up_pack_path,O_RDONLY|O_NOFOLLOW|O_DIRECT);need(fd>=0,"Sealed Direct Gate/Up sample required");
    // One bounded aligned source window, independent from the model reader.
    void*raw=nullptr;need(posix_memalign(&raw,65536,2u<<20)==0,"Gate/Up sample window unavailable");
    std::array<std::vector<unsigned char>,2>weights;for(auto&w:weights)w.resize(10*537600);
    const unsigned physical[]={0,127,347},slots[]={0,4,9};
    for(unsigned role=0;role<2;++role)for(unsigned j=0;j<3;++j){
        const uint64_t at=uint64_t(physical[j])*1540096+role*537600,aligned=at&~uint64_t(16383);const size_t skip=at-aligned,n=(skip+537600+16383)&~size_t(16383);
        need(pread(fd,raw,n,aligned)==ssize_t(n),"Complete Gate/Up source sample read required");std::memcpy(weights[role].data()+slots[j]*537600,static_cast<unsigned char*>(raw)+skip,537600);
    }
    need(close(fd)==0,"Gate/Up sample descriptor did not close");std::free(raw);raw=nullptr;
    Json cases=Json::array();unsigned graphs=0;const auto deadline=Clock::now()+std::chrono::seconds(240);
    for(unsigned tokens:{1u,2u,3u}){
        admit();auto*backend=ggml_backend_vk_init(0);need(backend,"Gate/Up Vulkan backend unavailable");
        ggml_init_params p{};p.mem_size=64*ggml_tensor_overhead()+2*ggml_graph_overhead_custom(32,false);p.no_alloc=true;
        auto*ctx=ggml_init(p);need(ctx,"Gate/Up metadata unavailable");
        auto*gate=ggml_new_tensor_3d(ctx,GGML_TYPE_Q2_K,2560,640,10);auto*up=ggml_dup_tensor(ctx,gate);
        auto*x=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,2560,1,tokens);auto*ids=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,6,tokens);
        for(auto*t:{gate,up,x,ids})ggml_set_input(t);
        std::array<ggml_tensor*,2>out{};std::array<ggml_cgraph*,2>g{};
        for(unsigned arm=0;arm<2;++arm){
            auto*a=ggml_mul_mat_id(ctx,gate,x,ids);auto*b=ggml_mul_mat_id(ctx,up,x,ids);out[arm]=ggml_swiglu_split(ctx,a,b);ggml_set_output(out[arm]);
            g[arm]=ggml_new_graph_custom(ctx,32,false);ggml_build_forward_expand(g[arm],out[arm]);
        }
        auto*canary=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,128);ggml_set_input(canary);ggml_set_output(canary);
        auto*buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);need(buffer,"Gate/Up fixture bounded buffer unavailable");
        for(unsigned role=0;role<2;++role)ggml_backend_tensor_set(role?up:gate,weights[role].data(),0,weights[role].size());
        std::vector<float>activation(tokens*2560);for(unsigned t=0;t<tokens;++t)for(unsigned col=0;col<2560;++col)activation[t*2560+col]=float(int((col+3*t)%13)-6)/1009.0f;
        std::vector<int>selected(tokens*6);for(unsigned t=0;t<tokens;++t)for(unsigned e=0;e<6;++e)selected[t*6+e]=slots[(e+t)%3];
        std::array<float,128>guard{};guard.fill(42.125f);ggml_backend_tensor_set(x,activation.data(),0,activation.size()*4);ggml_backend_tensor_set(ids,selected.data(),0,selected.size()*4);ggml_backend_tensor_set(canary,guard.data(),0,sizeof(guard));
        // F64 reference scans every actual encoded weight once per role/slot.
        std::array<std::vector<double>,2>sums;for(auto&s:sums)s.assign(3*640*13,0);
        for(unsigned role=0;role<2;++role)for(unsigned e=0;e<3;++e)for(unsigned row=0;row<640;++row)for(unsigned col=0;col<2560;++col)
            sums[role][(e*640+row)*13+col%13]+=double(decoded(weights[role].data()+slots[e]*537600,row*2560+col));
        std::vector<double>reference(tokens*6*640);
        for(unsigned t=0;t<tokens;++t)for(unsigned e=0;e<6;++e)for(unsigned row=0;row<640;++row){double a=0,b=0;unsigned slot=(e+t)%3;
            for(unsigned col=0;col<13;++col){a+=sums[0][(slot*640+row)*13+col]*double(activation[t*2560+col]);b+=sums[1][(slot*640+row)*13+col]*double(activation[t*2560+col]);}
            reference[(t*6+e)*640+row]=(a/(1+std::exp(-a)))*b;
        }
        ggml_backend_synchronize(backend);checkpoint();double maximum=0;std::uint64_t before=qwen_app_gate_up_trial_selections();
        auto verify=[&](unsigned arm){std::vector<float>actual(reference.size());ggml_backend_tensor_get(out[arm],actual.data(),0,actual.size()*4);
            for(size_t i=0;i<actual.size();++i){double error=std::abs(double(actual[i])-reference[i]);need(std::isfinite(actual[i])&&error<=1e-5+2e-4*std::abs(reference[i]),"Fused Gate/Up differs from complete F64 reference");maximum=std::max(maximum,error);}
            std::array<float,128>observed{};ggml_backend_tensor_get(canary,observed.data(),0,sizeof(observed));need(observed==guard,"Gate/Up device canary changed");};
        auto compute=[&](unsigned arm){admit();need(Clock::now()<deadline&&graphs<128,"Gate/Up finite bound reached");qwen_app_gate_up_trial_select(arm==1);auto start=Clock::now();need(ggml_backend_graph_compute(backend,g[arm])==GGML_STATUS_SUCCESS,"Gate/Up GPU call failed; retain owner");ggml_backend_synchronize(backend);auto done=Clock::now();checkpoint();auto checked=Clock::now();++graphs;
            return std::array<double,2>{std::chrono::duration<double,std::micro>(done-start).count(),std::chrono::duration<double,std::micro>(checked-start).count()};};
        for(unsigned i=0;i<4;++i){compute(i%2);verify(i%2);}Json arms=Json::array();
        for(unsigned phase=0;phase<4;++phase){unsigned arm=phase==1||phase==2;Json backend_us=Json::array(),whole_us=Json::array();for(unsigned sample=0;sample<8;++sample){auto time=compute(arm);backend_us.push_back(time[0]);whole_us.push_back(time[1]);}verify(arm);arms.push_back({{"candidate",arm==1},{"backend_samples_us",backend_us},{"whole_samples_us",whole_us}});}
        auto selected_count=qwen_app_gate_up_trial_selections()-before;need((tokens<=2&&selected_count>0)||(tokens==3&&selected_count==0),"Gate/Up selected-path/fallback coverage differs");
        qwen_app_gate_up_trial_select(false);ggml_backend_synchronize(backend);checkpoint();ggml_backend_buffer_free(buffer);ggml_free(ctx);ggml_backend_free(backend);checkpoint();
        cases.push_back({{"tokens",tokens},{"arms",arms},{"candidate_pipeline_selections",selected_count},{"maximum_absolute_error",maximum},{"all_F64_outputs_passed",true},{"canary_passed",true},{"positive_retirement",true}});
        stage("Gate_Up_fixture_case_completed_positive_retirement");
    }
    return {{"GPU_graphs",graphs},{"cases",cases},{"actual_Expert_Q2_payloads",true},{"all_F64_outputs_passed",true}};
}
}}
