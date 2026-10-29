// SPDX-License-Identifier: MIT
// Bounded actual-weight scheduling comparison, without loading an LLM.
#include <expert_q2_ready_graph.h>
#include "Q2-bundle-plan.private.h"
#include <system_memory.h>
#include <device_buffer_budget.h>
#include <ggml-alloc.h>
#include <ggml-backend.h>
#include <ggml-vulkan.h>
#include <nlohmann/json.hpp>
#include <ps5platform/heap.h>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <exception>
#include <fcntl.h>
#include <thread>
#include <sys/stat.h>
#include <unistd.h>
extern "C" int qwen_app_Q2_bundle_fixture_descriptor();
namespace qwen_app {namespace {
using Json=nlohmann::json;using Clock=std::chrono::steady_clock;using Key=std::array<std::uint64_t,10>;
constexpr std::size_t stride=1540096,group_bytes=5*stride;
void need(bool b,const char*m){if(!b)throw std::runtime_error(m);}
std::uint64_t ns(){return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();}
Key key(int fd){struct stat s{};need(fd>=0&&(fcntl(fd,F_GETFL)&O_DIRECT)&&!fstat(fd,&s)&&S_ISREG(s.st_mode),"Owned Q2 overlap Direct source required");return{std::uint64_t(s.st_dev),std::uint64_t(s.st_ino),std::uint64_t(s.st_mode),std::uint64_t(s.st_uid),std::uint64_t(s.st_gid),std::uint64_t(s.st_size),std::uint64_t(s.st_mtim.tv_sec),std::uint64_t(s.st_mtim.tv_nsec),std::uint64_t(s.st_ctim.tv_sec),std::uint64_t(s.st_ctim.tv_nsec)};}
struct Worker{std::thread*thread=nullptr;std::atomic<bool>done{false};std::exception_ptr error;std::uint64_t begin=0,end=0;};
struct Fixture{
    ggml_backend_t backend=nullptr;ggml_context*ctx=nullptr;ggml_backend_buffer_t buffer=nullptr;void*window=nullptr;int fd=-1;Key source{};
    std::array<ReadyExpertGraphInputs,2>a{};std::array<ggml_cgraph*,4>graphs{};ggml_tensor*output=nullptr,*contributions=nullptr,*canary=nullptr;
    void(*checkpoint)();void(*stage)(const char*);Clock::time_point deadline=Clock::now()+std::chrono::seconds(120);unsigned completed_graphs=0;
    Fixture(void(*c)(),void(*s)(const char*)):checkpoint(c),stage(s){
        fd=qwen_app_Q2_bundle_fixture_descriptor();source=key(fd);need(source[2]==0100444&&!source[3]&&!source[4]&&source[5]>=10*stride,"Exact sealed bundle pack required");
        for(unsigned i=1;i<10;++i)need(source[i]==Q2_bundle_expected_identity[i],"Overlap bundle source identity differs");
        need(!posix_memalign(&window,16384,16u<<20)&&window&&ps5_heap_owns(window),"Two tracked independent Q2 CPU windows required");
        backend=ggml_backend_vk_init(0);need(backend,"Overlap Vulkan backend unavailable");ggml_init_params p{};p.no_alloc=true;p.mem_size=800*ggml_tensor_overhead()+8*ggml_graph_overhead_custom(256,false);
        ctx=ggml_init(p);need(ctx,"Overlap graph metadata unavailable");auto*x=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,1);ggml_set_input(x);
        contributions=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,10);output=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,1);ggml_set_input(contributions);ggml_set_output(contributions);ggml_set_output(output);
        canary=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,128);ggml_set_input(canary);ggml_set_output(canary);
        for(unsigned group=0;group<2;++group){auto&v=a[group];v.count=5;v.activation=x;v.contributions=contributions;
            v.gate=ggml_new_tensor_3d(ctx,GGML_TYPE_Q2_K,2560,640,5);v.up=ggml_new_tensor_3d(ctx,GGML_TYPE_Q2_K,2560,640,5);v.down=ggml_new_tensor_3d(ctx,GGML_TYPE_Q2_0,640,2560,5);
            v.slots=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,5,1);v.weights=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,1,5);ggml_set_input(v.slots);ggml_set_input(v.weights);
            for(unsigned i=0;i<5;++i)v.original_ordinals[i]=group*5+i;}
        graphs[0]=build_Q2_serial_ready_graph(ctx,a,output);graphs[1]=build_Q2_ready_expert_graph(ctx,a[0]);graphs[2]=build_Q2_ready_expert_graph(ctx,a[1]);graphs[3]=build_ready_expert_reduction(ctx,contributions,output);
        const auto type=ggml_backend_get_default_buffer_type(backend);const auto planned=ggml_backend_alloc_ctx_tensors_from_buft_size(ctx,type);
        need(planned&&planned<=(48u<<20),"Q2 overlap fixture exceeds bounded device scope");(void)admit_native_system_memory();buffer=ggml_backend_alloc_ctx_tensors(ctx,backend);need(buffer&&ggml_backend_buffer_get_size(buffer)<=48u<<20,"Q2 overlap device allocation failed");
        std::array<float,2560>activation{};for(unsigned i=0;i<2560;++i)activation[i]=float(int(i%13)-6)/1009.0f;ggml_backend_tensor_set(x,activation.data(),0,sizeof(activation));
        std::array<float,128>guard;guard.fill(42.125f);ggml_backend_tensor_set(canary,guard.data(),0,sizeof(guard));
        for(unsigned group=0;group<2;++group){std::array<std::int32_t,5>ids{0,1,2,3,4};std::array<float,5>w{};for(unsigned i=0;i<5;++i)w[i]=float(group*5+i+1)/256.0f;
            ggml_backend_tensor_set(a[group].slots,ids.data(),0,sizeof(ids));ggml_backend_tensor_set(a[group].weights,w.data(),0,sizeof(w));}
        ggml_backend_synchronize(backend);checkpoint();
    }
    void bounded(){need(Clock::now()<deadline&&completed_graphs<40,"Bounded Q2 overlap fixture exhausted");}
    void read(unsigned group){need(Clock::now()<deadline,"Q2 overlap I/O deadline exhausted");need(group<2&&key(fd)==source&&qualified_system_headroom(observe_native_system_memory())>=256u<<20,"Q2 overlap source or system reserve changed");
        auto*target=static_cast<unsigned char*>(window)+group*(8u<<20);const auto got=pread(fd,target,group_bytes,group*group_bytes);
        need(got==ssize_t(group_bytes)&&key(fd)==source,"Q2 overlap read incomplete or identity changed");}
    void upload(unsigned group){bounded();const auto*raw=static_cast<const unsigned char*>(window)+group*(8u<<20);
        for(unsigned i=0;i<5;++i){const auto*p=raw+i*stride;ggml_backend_tensor_set(a[group].gate,p,i*537600,537600);ggml_backend_tensor_set(a[group].up,p+537600,i*537600,537600);ggml_backend_tensor_set(a[group].down,p+1075200,i*460800,460800);}
        ggml_backend_synchronize(backend);checkpoint();}
    void compute(unsigned graph){bounded();need(graph<4,"Known Q2 overlap graph required");stage("Q2_overlap_before_graph");
        need(ggml_backend_graph_compute(backend,graphs[graph])==GGML_STATUS_SUCCESS,"Q2 overlap GPU graph incomplete; owners retained");ggml_backend_synchronize(backend);checkpoint();++completed_graphs;stage("Q2_overlap_graph_positive_completion");}
    Json run(unsigned mode){bounded();need(mode<3,"Known Q2 overlap mode required");std::vector<float>poison(25600,NAN);ggml_backend_tensor_set(contributions,poison.data(),0,poison.size()*4);ggml_backend_tensor_set(output,poison.data(),0,2560*4);ggml_backend_synchronize(backend);checkpoint();
        const auto start=ns();read(0);upload(0);std::uint64_t read_begin=0,read_end=0,graph_begin=0,graph_end=0;
        if(mode==2){auto*w=new Worker;w->thread=new std::thread([&,w]{try{w->begin=ns();read(1);w->end=ns();}catch(...){w->error=std::current_exception();}w->done.store(true,std::memory_order_release);});
            graph_begin=ns();compute(1);graph_end=ns();while(!w->done.load(std::memory_order_acquire)){bounded();usleep(100);}
            w->thread->join();if(w->error)std::rethrow_exception(w->error);read_begin=w->begin;read_end=w->end;delete w->thread;delete w;upload(1);compute(2);compute(3);
        }else{read_begin=ns();read(1);read_end=ns();upload(1);graph_begin=ns();if(mode==0)compute(0);else{compute(1);compute(2);compute(3);}graph_end=ns();}
        const auto end=ns();std::vector<float>actual(28160);ggml_backend_tensor_get(contributions,actual.data(),0,25600*4);ggml_backend_tensor_get(output,actual.data()+25600,0,2560*4);
        for(float f:actual)need(std::isfinite(f),"Q2 overlap output is nonfinite or incomplete");std::array<float,128>guard;ggml_backend_tensor_get(canary,guard.data(),0,sizeof(guard));for(float f:guard)need(f==42.125f,"Q2 overlap canary changed");
        if(reference.empty())reference=actual;else need(actual==reference,"Q2 scheduling changed complete F32 contributions or original reduction");
        const auto intersect=std::min(read_end,graph_end)>std::max(read_begin,graph_begin)?std::min(read_end,graph_end)-std::max(read_begin,graph_begin):0;
        return{{"mode",mode},{"wall_ns",end-start},{"read_calls",2},{"physical_bytes",2*group_bytes},{"GPU_graphs",mode?3:1},{"read1_begin_ns",read_begin},{"read1_end_ns",read_end},{"graph0_begin_ns",graph_begin},{"graph0_end_ns",graph_end},{"read_and_GPU_producer_interval_intersection_ns",intersect},{"exact_full_F32_contributions_and_reduction",true},{"CPU_worker_never_writes_GPU_banks",true}};
    }
    std::vector<float>reference;
    void close_completed(){need(key(fd)==source,"Q2 overlap source changed before retirement");ggml_backend_synchronize(backend);checkpoint();ggml_backend_buffer_free(buffer);buffer=nullptr;ggml_free(ctx);ctx=nullptr;ggml_backend_free(backend);backend=nullptr;checkpoint();free(window);window=nullptr;}
};
}
nlohmann::json run_expert_Q2_overlap_fixture(void(*checkpoint)(),void(*stage)(const char*)){
    need(checkpoint&&stage,"Q2 overlap completion operations required");auto*f=new Fixture(checkpoint,stage);Json cases=Json::array();
    for(unsigned mode:{0u,1u,2u})f->run(mode);for(unsigned mode:{0u,1u,2u,2u,1u,0u})cases.push_back(f->run(mode));
    const auto graphs=f->completed_graphs;f->close_completed();delete f;
    return{{"schema","ps5-qwen-Q2-overlap-component-result-v1"},{"completed",true},{"cases",cases},{"warmup_modes",{0,1,2}},{"GPU_graphs",graphs},{"model_loads",0},{"actual_quantized_Expert_triplets",10},{"same_complete_F32_and_reads",true},{"all_source_and_device_owners_positively_retired",true},{"component_not_model_tok_s",true},{"mixed_layer_fixed_asset_cohort",true},{"hardware_timestamp_queries",false},{"automatic_retries",0}};
}
}
