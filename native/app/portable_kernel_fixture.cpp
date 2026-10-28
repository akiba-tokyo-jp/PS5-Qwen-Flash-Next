// SPDX-License-Identifier: MIT
#include "portable_kernel_fixture.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-alloc.h"
#include "ggml-vulkan.h"
#include "system_memory.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <vector>
namespace {
unsigned workgroup_mode=0;
using Clock=std::chrono::steady_clock;
using Json=nlohmann::json;
std::uint64_t graphs=0;
struct Fixture {
    ggml_backend_t backend=nullptr;
    ggml_context*ctx=nullptr;
    ggml_backend_buffer_t buffer=nullptr;
    std::array<ggml_cgraph*,2> graph{};
    std::array<std::vector<ggml_tensor*>,2> output{};
    ggml_tensor*canary=nullptr;
    std::vector<double> expected;
    void(*checkpoint)();void(*stage)(const char*);
    Clock::time_point deadline;
    double maximum=0;
    explicit Fixture(void(*c)(),void(*s)(const char*),Clock::time_point d):checkpoint(c),stage(s),deadline(d){
        backend=ggml_backend_vk_init(0);if(!backend)throw std::runtime_error("Portable fixture GPU backend is unavailable");
        ggml_init_params p{};p.no_alloc=true;p.mem_size=128*ggml_tensor_overhead()+2*ggml_graph_overhead_custom(64,false);
        ctx=ggml_init(p);if(!ctx)throw std::runtime_error("Portable fixture metadata allocation failed");
        for(auto&g:graph)g=ggml_new_graph_custom(ctx,64,false);
    }
    void allocate(){
        canary=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,128);ggml_set_input(canary);ggml_set_output(canary);
        buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);if(!buffer)throw std::runtime_error("Portable fixture GPU allocation failed");
        std::array<float,128> values{};values.fill(42.125f);ggml_backend_tensor_set(canary,values.data(),0,sizeof(values));
        ggml_backend_synchronize(backend);checkpoint();
    }
    void check(unsigned mode){
        std::vector<float> values;std::size_t offset=0;
        for(auto*t:output[mode]){
            const auto count=std::size_t(ggml_nelements(t));values.resize(count);
            if(ggml_is_contiguous(t))ggml_backend_tensor_get(t,values.data(),0,count*4);
            else{
                if(t->nb[0]!=4||t->ne[2]!=1||t->ne[3]!=1)throw std::runtime_error("Portable output view geometry differs");
                for(std::int64_t row=0;row<t->ne[1];++row)
                    ggml_backend_tensor_get(t,values.data()+row*t->ne[0],row*t->nb[1],t->ne[0]*4);
            }
            for(std::size_t i=0;i<count;++i){const auto ref=expected.at(offset+i),error=std::abs(double(values[i])-ref);
                if(!std::isfinite(values[i])||!std::isfinite(ref)||error>1e-5+1e-5*std::abs(ref))
                    throw std::runtime_error("Portable fixture original-precision F64 reference failed; GPU owner retained");
                maximum=std::max(maximum,error);
            }offset+=count;
        }
        if(offset!=expected.size())throw std::runtime_error("Portable fixture omitted an output");
        std::array<float,128> guard{};ggml_backend_tensor_get(canary,guard.data(),0,sizeof(guard));
        if(!std::all_of(guard.begin(),guard.end(),[](float x){return x==42.125f;}))
            throw std::runtime_error("Portable fixture output canary changed");
    }
    double compute(unsigned mode){
        if(Clock::now()>deadline||graphs>=400)throw std::runtime_error("Portable fixture finite execution bound exhausted");
        (void)qwen_app::admit_native_system_memory();workgroup_mode=mode;
        stage("portable_kernel_before_finite_graph");const auto start=Clock::now();
        if(ggml_backend_graph_compute(backend,graph[mode])!=GGML_STATUS_SUCCESS)
            throw std::runtime_error("Portable fixture GPU completion failed; owner retained");
        ggml_backend_synchronize(backend);checkpoint();++graphs;
        const auto elapsed=std::chrono::duration<double,std::micro>(Clock::now()-start).count();
        if(!std::isfinite(elapsed)||elapsed<=0)throw std::runtime_error("Portable fixture clock did not advance");
        stage("portable_kernel_graph_positive_completion");return elapsed;
    }
    Json measure(const char*kind,unsigned width){
        for(unsigned i=0;i<4;++i){compute(i%2);check(i%2);}
        Json arms=Json::array();
        for(unsigned arm=0;arm<4;++arm){const auto mode=arm==1||arm==2?1u:0u;std::array<double,8> times{};
            for(auto&t:times)t=compute(mode);check(mode);
            auto sorted=times;std::sort(sorted.begin(),sorted.end());double sum=0;for(auto t:times)sum+=t;
            arms.push_back({{"candidate",mode==1},{"samples_us",times},{"mean_us",sum/8},{"median_us",(sorted[3]+sorted[4])/2}});
        }
        workgroup_mode=0;ggml_backend_synchronize(backend);checkpoint();
        // Unknown or failed completion never reaches this explicit release.
        ggml_backend_buffer_free(buffer);buffer=nullptr;ggml_free(ctx);ctx=nullptr;ggml_backend_free(backend);backend=nullptr;checkpoint();
        return {{"candidate",kind},{"width",width},{"arms",arms},{"reference_accumulation","F64"},
            {"maximum_absolute_error",maximum},{"finite_reference_and_canary_passed",true},{"GPU_graphs",36}};
    }
};
float x_value(unsigned col,unsigned vector){return float(int((col+3*vector)%13)-6)/1009.0f;}
float w_value(unsigned row,unsigned col){return float(int((row+col)%31)-15)/64.0f;}
void connect(Fixture&f,unsigned mode,ggml_tensor*t){ggml_set_output(t);f.output[mode].push_back(t);ggml_build_forward_expand(f.graph[mode],t);}
Json matrix_case(unsigned width,bool dual,void(*checkpoint)(),void(*stage)(const char*),Clock::time_point deadline){
    Fixture f(checkpoint,stage,deadline);const unsigned k=2560,first=dual?10240:512,second=dual?6144:0;
    auto*a=ggml_new_tensor_2d(f.ctx,dual?GGML_TYPE_BF16:GGML_TYPE_F32,k,first);
    auto*b=dual?ggml_new_tensor_2d(f.ctx,GGML_TYPE_BF16,k,second):nullptr;
    auto*packed=dual?ggml_new_tensor_2d(f.ctx,GGML_TYPE_BF16,k,first+second):nullptr;
    auto*x=ggml_new_tensor_2d(f.ctx,GGML_TYPE_F32,k,width);
    connect(f,0,ggml_mul_mat(f.ctx,a,x));
    if(dual){connect(f,0,ggml_mul_mat(f.ctx,b,x));auto*y=ggml_mul_mat(f.ctx,packed,x);
        auto*y0=ggml_view_2d(f.ctx,y,first,width,(first+second)*4,0);
        auto*y1=ggml_view_2d(f.ctx,y,second,width,(first+second)*4,first*4);
        // The two consumers retain original-stride views, with no per-token
        // weight concatenation or output-copy kernels hidden in the claim.
        connect(f,1,y0);connect(f,1,y1);
    }else connect(f,1,ggml_mul_mat(f.ctx,a,x));
    f.allocate();std::vector<float> input(k*width);for(unsigned v=0;v<width;++v)for(unsigned c=0;c<k;++c)input[v*k+c]=x_value(c,v);
    ggml_backend_tensor_set(x,input.data(),0,input.size()*4);
    std::array<std::array<double,31>,4> dot{};
    for(unsigned v=0;v<width;++v)for(unsigned r=0;r<31;++r)for(unsigned c=0;c<k;++c)dot[v][r]+=double(w_value(r,c))*input[v*k+c];
    for(unsigned part=0;part<(dual?2u:1u);++part)for(unsigned v=0;v<width;++v)for(unsigned r=0;r<(part?second:first);++r)f.expected.push_back(dot[v][r%31]);
    if(dual){std::vector<ggml_bf16_t> weights(std::size_t(k)*(first+second));
        for(unsigned r=0;r<first+second;++r)for(unsigned c=0;c<k;++c)weights[std::size_t(r)*k+c]=ggml_fp32_to_bf16(w_value(r<first?r:r-first,c));
        ggml_backend_tensor_set(a,weights.data(),0,std::size_t(first)*k*2);ggml_backend_tensor_set(b,weights.data()+std::size_t(first)*k,0,std::size_t(second)*k*2);
        ggml_backend_tensor_set(packed,weights.data(),0,weights.size()*2);
    }else{std::vector<float> weights(std::size_t(k)*first);for(unsigned r=0;r<first;++r)for(unsigned c=0;c<k;++c)weights[std::size_t(r)*k+c]=w_value(r,c);
        ggml_backend_tensor_set(a,weights.data(),0,weights.size()*4);}
    return f.measure(dual?"shared-input-packed-projection":"router-large-workgroup",width);
}
Json norm_case(unsigned width,void(*checkpoint)(),void(*stage)(const char*),Clock::time_point deadline){
    Fixture f(checkpoint,stage,deadline);constexpr unsigned n=128,heads=48;const auto rows=heads*width;
    auto*x=ggml_new_tensor_2d(f.ctx,GGML_TYPE_F32,n,rows);auto*w=ggml_new_tensor_1d(f.ctx,GGML_TYPE_F32,n);
    auto*g=ggml_new_tensor_2d(f.ctx,GGML_TYPE_F32,2*n,rows);auto*gate=ggml_view_2d(f.ctx,g,n,rows,2*n*4,0);
    for(unsigned mode=0;mode<2;++mode){auto*norm=ggml_mul(f.ctx,ggml_rms_norm(f.ctx,x,1e-6f),w);
        auto*active=mode?ggml_cont(f.ctx,gate):gate;connect(f,mode,ggml_mul(f.ctx,norm,ggml_sigmoid(f.ctx,active)));}
    f.allocate();std::vector<float> input(n*rows),weight(n),gates(2*n*rows);
    for(unsigned c=0;c<n;++c)weight[c]=1.0f+float(c%7)/64;
    for(unsigned r=0;r<rows;++r){double sum=0;for(unsigned c=0;c<n;++c){auto v=x_value(c,r);input[r*n+c]=v;sum+=double(v)*v;gates[r*2*n+c]=float(int(c%19)-9)/17;}
        const double scale=1/std::sqrt(sum/n+double(1e-6f));
        for(unsigned c=0;c<n;++c)f.expected.push_back(double(input[r*n+c])*scale*weight[c]/(1+std::exp(-double(gates[r*2*n+c]))));}
    ggml_backend_tensor_set(x,input.data(),0,input.size()*4);ggml_backend_tensor_set(w,weight.data(),0,weight.size()*4);ggml_backend_tensor_set(g,gates.data(),0,gates.size()*4);
    return f.measure("contiguous-gate-sigmoid-multiply",width);
}
}
extern "C" unsigned qwen_app_portable_workgroup_mode(){return workgroup_mode;}
namespace qwen_app {
nlohmann::json run_portable_kernel_fixture(void(*checkpoint)(),void(*stage)(const char*)){
    if(!checkpoint||!stage||graphs)throw std::invalid_argument("One bounded portable kernel fixture is required");
    const auto deadline=Clock::now()+std::chrono::seconds(120);Json results=Json::array();
    for(unsigned width:{1u,2u,4u})results.push_back(matrix_case(width,false,checkpoint,stage,deadline));
    for(unsigned width:{1u,2u,4u})results.push_back(matrix_case(width,true,checkpoint,stage,deadline));
    for(unsigned width:{1u,2u,4u})results.push_back(norm_case(width,checkpoint,stage,deadline));
    return {{"schema","ps5-qwen-portable-kernel-comparison-v1"},{"completed",true},{"cases",results},
        {"GPU_graphs",graphs},{"maximum_GPU_graphs",400},{"model_loaded",false},{"synthetic_fixture_not_model_speed",true},
        {"all_outputs_reference_valid",true},{"all_backends_positively_retired",true},{"automatic_retries",0}};
}
}
