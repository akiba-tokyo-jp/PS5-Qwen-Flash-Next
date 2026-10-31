// SPDX-License-Identifier: MIT
#pragma once
#include "finite_greedy.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-vulkan.h"
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <vector>
namespace qwen_app {namespace greedy_gpu_fixture {
using Json=nlohmann::json;using Clock=std::chrono::steady_clock;
inline void need(bool v,const char*m){if(!v)throw std::runtime_error(m);}
inline Json run(void(*checkpoint)(),void(*stage)(const char*),void(*admit)()){
    Json cases=Json::array();unsigned graphs=0;const auto deadline=Clock::now()+std::chrono::seconds(180);
    for(unsigned scenario=0;scenario<11;++scenario){
        const unsigned cols=scenario==0?31:scenario==1?65:scenario==2?256:248320;
        const unsigned rows=scenario==2||scenario==4||scenario==8?2:1;const bool invalid=scenario>=8;
        std::vector<float>source(std::size_t(cols)*rows+128,42.125f);
        for(unsigned row=0;row<rows;++row)for(unsigned i=0;i<cols;++i)source[64+std::size_t(row)*cols+i]=float(int((i*37+row*17)%157)-78)*0.01f;
        if(scenario==1||scenario==5){source[65]=9.f;source[128]=9.f;}
        if(scenario==6)for(unsigned i=0;i<cols;++i)source[64+i]=i%2?-0.f:0.f;
        if(scenario==7)std::fill(source.begin()+64,source.end()-64,-std::numeric_limits<float>::max());
        if(scenario==8)source[64+cols-1]=std::numeric_limits<float>::quiet_NaN();
        if(scenario==9)source[64+cols/2]=std::numeric_limits<float>::infinity();
        if(scenario==10)source[64+cols/2]=-std::numeric_limits<float>::infinity();
        std::vector<std::int32_t>reference(rows);
        for(unsigned row=0;row<rows;++row){try{reference[row]=finite_greedy(source.data()+64+std::size_t(row)*cols,cols);}catch(const std::exception&){reference[row]=-1;}}
        admit();auto*backend=ggml_backend_vk_init(0);need(backend,"Greedy fixture Vulkan backend unavailable");
        ggml_init_params params{};params.mem_size=32*ggml_tensor_overhead()+ggml_graph_overhead_custom(16,false);params.no_alloc=true;
        auto*ctx=ggml_init(params);need(ctx,"Greedy fixture metadata unavailable");
        auto*input=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,source.size());ggml_set_input(input);
        auto*x=ggml_view_2d(ctx,input,cols,rows,cols*4,64*4);
        auto*storage=ggml_new_tensor_1d(ctx,GGML_TYPE_I32,rows+128);ggml_set_input(storage);ggml_set_output(storage);
        auto*out=ggml_argmax(ctx,x);out->view_src=storage;out->view_offs=64*4;ggml_set_output(out);
        auto*graph=ggml_new_graph_custom(ctx,16,false);ggml_build_forward_expand(graph,out);
        need(ggml_backend_supports_op(backend,out),"Greedy fixture may not fall back to CPU");
        auto*buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);need(buffer,"Greedy fixture owned buffer unavailable");
        std::vector<std::int32_t>guard(rows+128,0x625A35A3),observed(rows),whole_guard(rows+128);
        std::vector<float>cpu(std::size_t(cols)*rows),whole_source(source.size());
        ggml_backend_tensor_set(input,source.data(),0,source.size()*4);ggml_backend_tensor_set(storage,guard.data(),0,guard.size()*4);
        auto verify=[&](){
            ggml_backend_tensor_get(storage,whole_guard.data(),0,whole_guard.size()*4);
            for(unsigned i=0;i<whole_guard.size();++i)need(whole_guard[i]==(i>=64&&i<64+rows?reference[i-64]:guard[i]),"Greedy result or output canary differs");
            ggml_backend_tensor_get(input,whole_source.data(),0,whole_source.size()*4);
            need(std::memcmp(source.data(),whole_source.data(),source.size()*4)==0,"Greedy read-only input or input canary changed");
        };
        auto compute=[&](){
            admit();need(Clock::now()<deadline&&graphs<110,"Greedy fixture finite bound reached");const auto begin=Clock::now();
            need(ggml_backend_graph_compute(backend,graph)==GGML_STATUS_SUCCESS,"Greedy GPU graph failed; retain owner");ggml_backend_synchronize(backend);
            ggml_backend_tensor_get(out,observed.data(),0,rows*4);const auto end=Clock::now();++graphs;
            need(observed==reference,"GPU greedy differs from complete CPU finite/first-index reference");checkpoint();
            return std::chrono::duration<double,std::micro>(end-begin).count();
        };
        auto cpu_route=[&](){
            admit();const auto begin=Clock::now();ggml_backend_tensor_get(x,cpu.data(),0,cpu.size()*4);
            for(unsigned row=0;row<rows;++row){std::int32_t token=-1;try{token=finite_greedy(cpu.data()+std::size_t(row)*cols,cols);}catch(const std::exception&){}
                need(token==reference[row],"CPU greedy readback/reference differs");}
            return std::chrono::duration<double,std::micro>(Clock::now()-begin).count();
        };
        compute();compute();verify();Json arms=Json::array();
        for(unsigned phase=0;phase<4;++phase){const bool gpu=phase==1||phase==2;Json times=Json::array();
            for(unsigned sample=0;sample<4;++sample)times.push_back(gpu?compute():cpu_route());
            verify();arms.push_back({{"GPU_selection",gpu},{"samples_us",times}});
        }
        ggml_backend_synchronize(backend);checkpoint();ggml_backend_buffer_free(buffer);ggml_free(ctx);ggml_backend_free(backend);checkpoint();
        cases.push_back({{"scenario",scenario},{"columns",cols},{"rows",rows},{"invalid_input",invalid},
            {"complete_reference_and_tie_order_exact",true},{"input_and_output_canaries_exact",true},
            {"CPU_control_includes_full_F32_readback",true},{"GPU_live_readback_bytes",rows*4},
            {"arms",arms},{"positive_retirement",true}});stage("greedy_fixture_case_completed_positive_retirement");
    }
    need(graphs==110,"Exact greedy graph count required");
    return {{"GPU_graphs",graphs},{"cases",cases},{"all_integer_outputs_and_finite_status_exact",true},
        {"all_canaries_passed",true},{"synthetic_inputs_only",true},{"learned_host_inference",false}};
}
}}
