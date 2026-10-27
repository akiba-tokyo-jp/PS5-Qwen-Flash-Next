// SPDX-License-Identifier: MIT
// Real GGML graph metadata and the application native adapter, with explicitly
// mocked device/system calls. No tensor arithmetic or physical I/O is executed.
#define QWEN_READY_SOURCE_NO_MAIN
#include "ready_source_coordinator.cpp"
#include "ready_expert_native.h"
#include "device_buffer_budget.h"
#include "system_memory.h"
#include "ggml-alloc.h"
#include "ggml-vulkan.h"
#include <ps5platform/kernel.h>
#include <cstring>
#include <type_traits>
static_assert(!std::is_copy_constructible_v<ReadyExpertNativeGraphs> && !std::is_copy_assignable_v<ReadyExpertNativeGraphs>);
static_assert(!std::is_copy_constructible_v<ReadyExpertExecution> && !std::is_copy_assignable_v<ReadyExpertExecution>);
struct ggml_backend {};
struct ggml_backend_buffer_type {};
struct ggml_backend_buffer {};
static ggml_backend_buffer_type mock_type;
static ggml_backend_buffer mock_buffer;
static std::string scenario;
static ReadyExpertWave *current_wave=nullptr;
static unsigned allocations=0,frees=0,computes=0,syncs=0,checkpoints=0,retains=0;
static bool allocated=false;
extern "C" bool ggml_backend_is_vk(ggml_backend_t){return scenario!="CPU-backend";}
extern "C" ggml_backend_buffer_type_t ggml_backend_get_default_buffer_type(ggml_backend_t){return &mock_type;}
extern "C" std::size_t ggml_backend_alloc_ctx_tensors_from_buft_size(ggml_context *,ggml_backend_buffer_type_t){return scenario=="oversized-plan"?17u<<20:1u<<20;}
extern "C" ggml_backend_buffer_t ggml_backend_alloc_ctx_tensors(ggml_context *,ggml_backend_t){++allocations;if(scenario=="allocation-failed")return nullptr;allocated=true;return &mock_buffer;}
extern "C" std::size_t ggml_backend_buffer_get_size(ggml_backend_buffer_t){return scenario=="oversized-buffer"?17u<<20:1u<<20;}
extern "C" void ggml_backend_buffer_free(ggml_backend_buffer_t){check(allocated);allocated=false;++frees;}
extern "C" ggml_status ggml_backend_graph_compute(ggml_backend_t,ggml_cgraph *graph){
    check(allocated&&ggml_graph_n_nodes(graph)>0);++computes;
    if(scenario!="one-graph"&&computes==1) {
        const auto until=deadline();while(current_wave->snapshot().role_returns!=30){check(std::chrono::steady_clock::now()<until);std::this_thread::yield();}
    }
    return scenario=="compute-failed"?GGML_STATUS_FAILED:GGML_STATUS_SUCCESS;
}
extern "C" void ggml_backend_synchronize(ggml_backend_t){++syncs;if(computes&&scenario=="sync-failed")throw std::runtime_error("Mock positive synchronization failed");}
extern "C" void qwen_native_driver_retain(){++retains;}
extern "C" std::int64_t sceKernelGetDirectMemorySize(){return 12ll<<30;}
extern "C" std::int32_t sceKernelAvailableDirectMemorySize(std::int64_t,std::int64_t,std::size_t,std::int64_t *physical,std::size_t *available){
    *physical=0;*available=scenario=="Direct-reserve"?(528u<<20)-1:2u<<30;return 0;
}
namespace qwen_app {
DeviceBufferStats native_model_device_stats(){return {scenario=="device-ledger"?1780ull<<20:512ull<<20,512ull<<20,2};}
SystemMemoryObservation observe_native_system_memory(){return {scenario=="Flexible-reserve"?128u<<20:512u<<20,16384,138739,
    scenario=="dispatch-memory"&&allocated?1000u:8192u,898,2974,206};}
SystemMemoryObservation admit_native_system_memory(){return observe_native_system_memory();}
}
static void checkpoint(){++checkpoints;if(computes&&scenario=="checkpoint-failed")throw std::runtime_error("Mock driver completion failed");}
static void stage(const char *text){if(scenario=="stage-failed"&&std::strstr(text,"before_first_group"))throw std::runtime_error("Mock durable plan failed");}
int main(int argc,char **argv){try{
    check(argc==2);scenario=argv[1];
    auto *ctx=ggml_init({2u<<20,nullptr,true});auto *roots_ctx=ggml_init({2u<<20,nullptr,true});check(ctx&&roots_ctx);
    auto *activation=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,2560,1,1);
    auto *contributions=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,10);
    auto *output=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,1);
    std::array<ReadyExpertGraphInputs,2> groups{};
    for(unsigned g=0;g<2;++g){
        auto &a=groups[g];a.activation=activation;a.contributions=contributions;a.count=5;
        std::array<ggml_tensor *,3> roots{};
        for(auto &r:roots)r=ggml_new_tensor_1d(roots_ctx,GGML_TYPE_BF16,split_bank_planes[g]*padded_bank_stride/2);
        a.gate=ggml_view_3d(ctx,roots[0],2560,640,split_bank_active[g],5120,padded_bank_stride,32);
        a.up=ggml_view_3d(ctx,roots[1],2560,640,split_bank_active[g],5120,padded_bank_stride,32);
        a.down=ggml_view_3d(ctx,roots[2],640,2560,split_bank_active[g],1280,padded_bank_stride,32);
        a.slots=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,5,1);a.weights=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,1,5,1);
        for(unsigned i=0;i<5;++i)a.original_ordinals[i]=g*5+i;
    }
    std::array<std::int32_t,10> experts{};std::array<unsigned,10> slots{};
    for(unsigned i=0;i<10;++i){experts[i]=i;slots[i]=i<5?i:48+i-5;}
    ReadyExpertWave wave(experts,slots,{{{{11,11,11}},{{22,22,22}}}},47,1,17,1);current_wave=&wave;
    ReadyExpertExecution execution;Source source;source.wave=&wave;
    ReadyExpertNativeGraphs native;ggml_backend backend;unsigned refused=0;
    const auto refuse=[&](auto op){try{op();}catch(const std::exception &){++refused;return;}throw std::runtime_error("Expected native ready adapter refusal missing");};
    if(scenario=="CPU-backend") {refuse([&]{native.prepare(ctx,&backend,groups,output,1,stage,checkpoint);});check(!allocations&&!computes);}
    else {
        native.prepare(ctx,&backend,groups,output,1,stage,checkpoint);
        if(scenario=="oversized-plan"||scenario=="allocation-failed"||scenario=="oversized-buffer"||
           scenario=="device-ledger"||scenario=="Flexible-reserve"||scenario=="Direct-reserve") {
            refuse([&]{native.allocate_workspace();});check(!computes&&!frees&&retains==1);
            refuse([&]{(void)native.operations();});
        }else {
            if(scenario=="before-allocation")refuse([&]{(void)native.operations();});
            native.allocate_workspace();
            if(scenario=="wrong-mask"||scenario=="wrong-epoch"||scenario=="wrong-order") {
                std::array<bool,10> mask{};for(unsigned i=0;i<5;++i)mask[i]=true;
                if(scenario=="wrong-mask")mask[9]=true;
                refuse([&]{ReadyExpertNativeGraphs::dispatch(scenario=="wrong-order"?ReadyGraphPhase::second_group:ReadyGraphPhase::first_group,
                    scenario=="wrong-epoch"?3:2,mask,&native);});check(!computes&&!frees&&retains==1);
            }else {
                if(scenario=="early-close")refuse([&]{native.close_completed(execution,wave);});
                const auto mode=scenario=="one-graph"?ReadyExecutionMode::one_graph_serial:ReadyExecutionMode::split_overlap;
                const auto run=[&]{execution.run(wave,mode,Source::fill,&source,native.operations(),1,deadline());};
                if(scenario=="compute-failed"||scenario=="sync-failed"||scenario=="checkpoint-failed"||scenario=="stage-failed"||scenario=="dispatch-memory") {
                    refuse(run);check(execution.snapshot().failed&&!execution.snapshot().completed&&!frees&&retains==1);
                    execution.retain_and_join_returned_source(deadline());refuse([&]{native.close_completed(execution,wave);});
                }else {
                    run();native.close_completed(execution,wave);check(frees==1&&!allocated&&retains==0&&computes==(mode==ReadyExecutionMode::one_graph_serial?1u:3u));
                    check(syncs==computes+2&&checkpoints==computes+4);
                    if(scenario=="repeat-close")refuse([&]{native.close_completed(execution,wave);});
                }
            }
        }
    }
    ggml_free(ctx);ggml_free(roots_ctx);
    std::cout<<"{\"passed\":true,\"refusals\":"<<refused<<",\"mock_compute_calls\":"<<computes
        <<",\"mock_workspace_frees\":"<<frees<<",\"mock_retains\":"<<retains
        <<",\"mock_synchronizations\":"<<syncs<<",\"mock_driver_checkpoints\":"<<checkpoints
        <<",\"physical_weight_bytes\":0,\"PS5_operations\":0,\"GPU_calls\":0}\n";return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
