// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <vector>
#include <nlohmann/json.hpp>

extern "C" void qwen_app_gdn_trial_select(bool);
extern "C" std::uint64_t qwen_app_gdn_trial_selections();

namespace qwen_app { namespace gdn_fixture {
using Clock=std::chrono::steady_clock;
using Json=nlohmann::json;
constexpr unsigned width=128;
constexpr float untouched=3.125f;
inline float value(std::size_t i,unsigned salt,float divisor) {
    return float(int((i*7+salt*11)%31)-15)/divisor;
}
struct Fixture {
    // An exception deliberately leaves GPU ownership to the ordinary OS close.
    ggml_backend_t backend=nullptr;
    ggml_context*context=nullptr;
    ggml_backend_buffer_t buffer=nullptr;
    std::array<ggml_cgraph*,2> graphs{};
    std::array<ggml_tensor*,2> output{};
    ggml_tensor*guard=nullptr;
    std::vector<double> expected;
    void(*checkpoint)();void(*stage)(const char*);void(*admit)();
    Clock::time_point deadline;
    unsigned&executions;
    double maximum=0;

    Fixture(void(*c)(),void(*s)(const char*),void(*a)(),Clock::time_point d,unsigned&e)
        :checkpoint(c),stage(s),admit(a),deadline(d),executions(e) {
        admit();
        backend=ggml_backend_vk_init(0);
        if(!backend)throw std::runtime_error("GDN fixture Vulkan backend unavailable");
        ggml_init_params p{};p.no_alloc=true;
        p.mem_size=32*ggml_tensor_overhead()+2*ggml_graph_overhead_custom(32,false);
        context=ggml_init(p);
        if(!context)throw std::runtime_error("GDN fixture metadata unavailable");
        for(auto&g:graphs)g=ggml_new_graph_custom(context,32,false);
    }
    double compute(unsigned arm) {
        if(Clock::now()>deadline||executions>=320)
            throw std::runtime_error("GDN fixture finite execution bound reached");
        admit();qwen_app_gdn_trial_select(arm!=0);
        stage("GDN_columns_before_bounded_graph");
        const auto start=Clock::now();
        if(ggml_backend_graph_compute(backend,graphs[arm])!=GGML_STATUS_SUCCESS)
            throw std::runtime_error("GDN fixture completion failed; GPU owner retained");
        ggml_backend_synchronize(backend);checkpoint();++executions;
        const auto elapsed=std::chrono::duration<double,std::micro>(Clock::now()-start).count();
        if(!std::isfinite(elapsed)||elapsed<=0)throw std::runtime_error("GDN fixture clock failed");
        stage("GDN_columns_graph_completed");return elapsed;
    }
    void check(unsigned arm) {
        std::vector<float> actual(expected.size());
        ggml_backend_tensor_get(output[arm],actual.data(),0,actual.size()*sizeof(float));
        for(std::size_t i=0;i<actual.size();++i) {
            const double error=std::abs(double(actual[i])-expected[i]);
            if(!std::isfinite(actual[i])||!std::isfinite(expected[i])||error>1e-6)
                throw std::runtime_error("GDN fixture F64 output or snapshot check failed; GPU owner retained");
            maximum=std::max(maximum,error);
        }
        std::array<float,128> canary{};
        ggml_backend_tensor_get(guard,canary.data(),0,sizeof(canary));
        if(!std::all_of(canary.begin(),canary.end(),[](float x){return x==42.125f;}))
            throw std::runtime_error("GDN fixture buffer canary changed; GPU owner retained");
    }
    Json measure() {
        const auto selections=qwen_app_gdn_trial_selections();
        for(unsigned i=0;i<4;++i){compute(i%2);check(i%2);}
        Json arms=Json::array();
        for(unsigned group=0;group<4;++group) {
            const unsigned arm=group==1||group==2?1:0;
            std::array<double,8> times{};for(auto&time:times)time=compute(arm);check(arm);
            auto sorted=times;std::sort(sorted.begin(),sorted.end());
            double sum=0;for(auto time:times)sum+=time;
            arms.push_back({{"candidate",arm==1},{"samples_us",times},
                {"mean_us",sum/8},{"median_us",(sorted[3]+sorted[4])/2}});
        }
        const auto selected=qwen_app_gdn_trial_selections()-selections;
        if(!selected)throw std::runtime_error("GDN candidate pipeline did not execute");
        qwen_app_gdn_trial_select(false);ggml_backend_synchronize(backend);checkpoint();
        // Release only after every submitted graph and readback has completed.
        ggml_backend_buffer_free(buffer);buffer=nullptr;
        ggml_free(context);context=nullptr;
        ggml_backend_free(backend);backend=nullptr;checkpoint();
        return {{"arms",arms},{"GPU_graphs",36},{"candidate_pipeline_selections",selected},
            {"maximum_absolute_error",maximum},{"F64_reference_all_outputs_passed",true},
            {"snapshot_unwritten_slots_preserved",true},{"canary_passed",true},
            {"positive_buffer_context_backend_retirement",true}};
    }
};
inline Json one(unsigned heads,unsigned qheads,unsigned tokens,unsigned sequences,
                unsigned snapshots,bool vector_gate,void(*checkpoint)(),
                void(*stage)(const char*),void(*admit)(),Clock::time_point deadline,unsigned&graphs) {
    Fixture f(checkpoint,stage,admit,deadline,graphs);
    auto tensor=[&](unsigned a,unsigned b,unsigned c,unsigned d){
        auto*t=ggml_new_tensor_4d(f.context,GGML_TYPE_F32,a,b,c,d);
        ggml_set_input(t);return t;
    };
    auto*q=tensor(width,qheads,tokens,1);auto*k=tensor(width,qheads,tokens,1);
    auto*v=tensor(width,heads,tokens,sequences);
    auto*g=tensor(vector_gate?width:1,heads,tokens,sequences);
    auto*beta=tensor(1,heads,tokens,sequences);
    auto*state=tensor(width,width,heads,sequences);
    for(unsigned arm=0;arm<2;++arm) {
        f.output[arm]=ggml_gated_delta_net(f.context,q,k,v,g,beta,state,snapshots);
        if(!ggml_backend_dev_supports_op(ggml_backend_get_device(f.backend),f.output[arm]))
            throw std::runtime_error("GDN fixture shape unsupported before allocation");
        ggml_set_output(f.output[arm]);ggml_build_forward_expand(f.graphs[arm],f.output[arm]);
    }
    f.guard=ggml_new_tensor_1d(f.context,GGML_TYPE_F32,128);
    ggml_set_input(f.guard);ggml_set_output(f.guard);
    f.buffer=ggml_backend_alloc_ctx_tensors(f.context,f.backend);
    if(!f.buffer)throw std::runtime_error("GDN fixture bounded buffer unavailable");
    auto values=[](ggml_tensor*t,unsigned salt,float divisor){
        std::vector<float>x(std::size_t(ggml_nelements(t)));
        for(std::size_t i=0;i<x.size();++i)x[i]=value(i,salt,divisor);
        return x;
    };
    auto qs=values(q,1,97),ks=values(k,2,113),vs=values(v,3,67);
    auto gs=values(g,4,1009),bs=values(beta,5,809),ss=values(state,6,223);
    for(auto&x:gs)x=-0.05f+x;for(auto&x:bs)x=0.4f+x;
    auto upload=[](ggml_tensor*t,const std::vector<float>&x){ggml_backend_tensor_set(t,x.data(),0,x.size()*4);};
    upload(q,qs);upload(k,ks);upload(v,vs);upload(g,gs);upload(beta,bs);upload(state,ss);
    std::array<float,128> guards{};guards.fill(42.125f);
    ggml_backend_tensor_set(f.guard,guards.data(),0,sizeof(guards));
    const std::size_t state_size=std::size_t(width)*width*heads*sequences;
    const std::size_t attention=std::size_t(width)*heads*tokens*sequences;
    f.expected.assign(attention+snapshots*state_size,untouched);
    std::vector<float> initial(f.expected.size(),untouched);
    for(auto*t:f.output)upload(t,initial);
    const double scale=float(1.0f/std::sqrt(float(width)));
    for(unsigned seq=0;seq<sequences;++seq)for(unsigned h=0;h<heads;++h) {
        const auto base=(std::size_t(seq)*heads+h)*width*width;
        std::vector<double> current(width*width);
        for(unsigned i=0;i<width*width;++i)current[i]=ss[base+i];
        for(unsigned t=0;t<tokens;++t) {
            const auto qo=(std::size_t(t)*qheads+h%qheads)*width;
            const auto vo=((std::size_t(seq)*tokens+t)*heads+h)*width;
            const auto bo=(std::size_t(seq)*tokens+t)*heads+h;
            for(unsigned col=0;col<width;++col) {
                double kv=0;
                for(unsigned row=0;row<width;++row) {
                    const auto gi=vector_gate?bo*width+row:bo;
                    kv+=std::exp(double(gs[gi]))*current[col*width+row]*ks[qo+row];
                }
                const double delta=(double(vs[vo+col])-kv)*bs[bo];double result=0;
                for(unsigned row=0;row<width;++row) {
                    const auto gi=vector_gate?bo*width+row:bo;
                    auto&x=current[col*width+row];
                    x=std::exp(double(gs[gi]))*x+double(ks[qo+row])*delta;
                    result+=x*qs[qo+row];
                }
                f.expected[vo+col]=result*scale;
            }
            const unsigned slot=tokens-1-t;
            if(slot<snapshots)for(unsigned i=0;i<width*width;++i)
                f.expected[attention+slot*state_size+base+i]=current[i];
        }
    }
    ggml_backend_synchronize(f.backend);checkpoint();
    auto result=f.measure();result.update({{"S_v",width},{"heads",heads},{"query_heads",qheads},
        {"tokens",tokens},{"sequences",sequences},{"snapshots",snapshots},{"vector_gate",vector_gate}});
    return result;
}
inline Json run(void(*checkpoint)(),void(*stage)(const char*),void(*admit)()) {
    const auto deadline=Clock::now()+std::chrono::seconds(180);
    unsigned graphs=0;Json cases=Json::array();
    for(bool vector_gate:{false,true})for(unsigned tokens:{1u,32u})for(unsigned snapshots:{1u,2u})
        cases.push_back(one(vector_gate?4:48,vector_gate?2:16,tokens,vector_gate?2:1,
                            snapshots,vector_gate,checkpoint,stage,admit,deadline,graphs));
    if(graphs!=288)throw std::runtime_error("GDN fixture omitted a declared graph");
    return {{"cases",cases},{"GPU_graphs",graphs},{"maximum_graphs",320},
        {"F64_reference_all_outputs_passed",true},{"maximum_absolute_error_limit",1e-6},
        {"warmup_graphs_per_case",4},{"ABBA_samples_per_arm",8},
        {"model_loads",0},{"full_model_speed_qualification",false}};
}
} }
