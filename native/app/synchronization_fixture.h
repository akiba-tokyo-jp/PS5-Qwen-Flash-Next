// SPDX-License-Identifier: MIT
#pragma once
#include "throughput_options.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include <nlohmann/json.hpp>
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <vector>
namespace qwen_app {namespace synchronization_fixture {
using Json=nlohmann::json;using Clock=std::chrono::steady_clock;
inline void need(bool b,const char*m){if(!b)throw std::runtime_error(m);}
inline Json run(unsigned base,void(*checkpoint)(),void(*stage)(const char*),void(*admit)()){
    Json cases=Json::array();unsigned graphs=0;const auto deadline=Clock::now()+std::chrono::seconds(180);
    for(unsigned scenario=0;scenario<3;++scenario){
        const unsigned n=scenario==0?256:scenario==1?65536:131072;
        std::array<std::vector<float>,4>input;for(auto&v:input)v.resize(n+128,42.125f);
        for(unsigned k=0;k<3;++k)for(unsigned i=0;i<n;++i)input[k][64+i]=float(int((i*(7+2*k)+13*k)%97)-48)/8.f;
        admit();auto*backend=ggml_backend_vk_init(0);need(backend,"Synchronization fixture Vulkan unavailable");
        ggml_init_params p{};p.no_alloc=true;p.mem_size=64*ggml_tensor_overhead()+ggml_graph_overhead_custom(64,false);
        auto*ctx=ggml_init(p);need(ctx,"Synchronization fixture metadata unavailable");
        std::array<ggml_tensor*,4>storage{},view{};
        for(unsigned k=0;k<4;++k){storage[k]=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,n+128);ggml_set_input(storage[k]);ggml_set_output(storage[k]);view[k]=ggml_view_1d(ctx,storage[k],n,64*4);}
        auto*a=scenario==2?ggml_cpy(ctx,view[0],view[3]):ggml_scale(ctx,view[0],2.f);
        auto*b=ggml_scale(ctx,view[1],3.f);
        auto*c=ggml_scale(ctx,view[2],4.f);c->view_src=storage[1];c->view_offs=64*4;
        ggml_set_output(a);ggml_set_output(b);ggml_set_output(c);
        auto*graph=ggml_new_graph_custom(ctx,64,false);ggml_build_forward_expand(graph,a);ggml_build_forward_expand(graph,b);ggml_build_forward_expand(graph,c);
        ggml_tensor*overwrite=nullptr;
        if(scenario==1){overwrite=ggml_scale(ctx,view[0],5.f);overwrite->view_src=storage[1];overwrite->view_offs=64*4;ggml_set_output(overwrite);ggml_build_forward_expand(graph,overwrite);}
        auto*d=ggml_add(ctx,a,c);ggml_set_output(d);ggml_build_forward_expand(graph,d);
        for(auto*t:{a,b,c,d})need(ggml_backend_supports_op(backend,t),"Synchronization fixture CPU fallback forbidden");
        if(overwrite)need(ggml_backend_supports_op(backend,overwrite),"WAW fixture CPU fallback forbidden");
        auto*buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);need(buffer,"Synchronization fixture device buffer unavailable");
        std::vector<float>expected_b(n),expected_d(n),expected_y=input[1],expected_z=input[3];
        for(unsigned i=0;i<n;++i){expected_b[i]=input[1][64+i]*3.f;expected_y[64+i]=scenario==1?input[0][64+i]*5.f:input[2][64+i]*4.f;expected_d[i]=input[0][64+i]*(scenario==2?1.f:2.f)+expected_y[64+i];if(scenario==2)expected_z[64+i]=input[0][64+i];}
        Json arms=Json::array();
        for(unsigned phase=0;phase<4;++phase){const bool candidate=phase==1||phase==2;qwen_throughput::mode=base|(candidate?8:0);const auto before=qwen_throughput::stats[11];Json samples=Json::array();
            for(unsigned sample=0;sample<3;++sample){
                admit();need(Clock::now()<deadline&&graphs<36,"Finite synchronization fixture bound reached");
                for(unsigned k=0;k<4;++k)ggml_backend_tensor_set(storage[k],input[k].data(),0,input[k].size()*4);
                const auto begin=Clock::now();need(ggml_backend_graph_compute(backend,graph)==GGML_STATUS_SUCCESS,"Synchronization fixture graph failed; retain owner");ggml_backend_synchronize(backend);const auto end=Clock::now();checkpoint();++graphs;
                samples.push_back(std::chrono::duration<double,std::micro>(end-begin).count());
                for(auto pair:{std::make_pair(b,&expected_b),std::make_pair(d,&expected_d),std::make_pair(storage[0],&input[0]),std::make_pair(storage[1],&expected_y),std::make_pair(storage[2],&input[2]),std::make_pair(storage[3],&expected_z)}){
                    std::vector<float>actual(pair.second->size());ggml_backend_tensor_get(pair.first,actual.data(),0,actual.size()*4);need(!std::memcmp(actual.data(),pair.second->data(),actual.size()*4),"Producer/consumer, independent prior write, transfer, WAW or canary differs");
                }
            }
            const auto selected=qwen_throughput::stats[11]-before;need(candidate?selected>0:selected==0,"Execution-only barrier fixture path coverage differs");
            arms.push_back({{"mode",base|(candidate?8:0)},{"samples_us",samples},{"execution_only_barriers",selected},{"complete_F32_bytes_and_canaries_exact",true}});
        }
        qwen_throughput::mode=base;ggml_backend_synchronize(backend);checkpoint();ggml_backend_buffer_free(buffer);ggml_free(ctx);ggml_backend_free(backend);checkpoint();
        cases.push_back({{"scenario",scenario},{"elements",n},{"independent_prior_write_retained",true},{"WAW_control",scenario==1},{"transfer_control",scenario==2},{"arms",arms},{"positive_retirement",true}});stage("synchronization_fixture_case_completed_positive_retirement");
    }
    need(graphs==36,"Every synchronization fixture graph required");return{{"completed",true},{"GPU_graphs",graphs},{"cases",cases},{"all_F32_bytes_and_canaries_exact",true},{"synthetic_inputs_only",true},{"model_loaded",false},{"learned_host_inference",false}};
}
}}
