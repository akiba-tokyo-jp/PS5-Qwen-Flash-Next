// SPDX-License-Identifier: MIT
#include "actual_scheduler_backend.cpp"
#include "ggml-cpu.h"
#include <cmath>
#include <iostream>
#include <limits>

static const void * source_key=nullptr;
static ggml_backend_buffer_type_t simulated_buffer=nullptr;
extern "C" bool qwen_app_model_reads_enabled() { return true; }
extern "C" bool qwen_app_model_source_range_metadata(const void * p, std::size_t) { return source_key && p==source_key; }
extern "C" void qwen_app_model_source_read_CPU(void *, const void *, std::size_t) { std::abort(); }
static void check(bool value) { if (!value) std::abort(); }
template<class F> static void rejected(F f) {
    try { f(); } catch (const std::runtime_error &) { return; }
    std::abort();
}
int main() {
    const size_t model_capacity=32*1256;
    const size_t original=model_capacity*GGML_SCHED_MAX_SPLIT_INPUTS*2*sizeof(ggml_tensor)+ggml_graph_overhead_custom(model_capacity,false);
    check(original > (512ull<<20));
    const auto measured=qwen_app_scheduler_context_required(7184);
    check(measured < qwen_app_scheduler_context_budget);
    rejected([] { qwen_app_scheduler_context_required(0); });
    rejected([] { qwen_app_scheduler_context_required(std::numeric_limits<size_t>::max()); });
    rejected([&] { qwen_app_scheduler_context_required(model_capacity); });
    // Exercise the actual GGML metadata allocator at the conservative bound,
    // including object/alignment overhead, without allocating tensor payloads.
    auto arena=ggml_init({qwen_app_scheduler_context_budget,nullptr,true});check(arena);
    for(size_t n=0;n<7184*GGML_SCHED_MAX_SPLIT_INPUTS*2;n++)check(ggml_new_tensor_1d(arena,GGML_TYPE_F32,1));
    check(ggml_new_graph_custom(arena,7184,false));
    const auto used=ggml_used_mem(arena);check(used<=measured);ggml_free(arena);
    auto backend=ggml_backend_cpu_init();check(backend);ggml_backend_cpu_set_n_threads(backend,1);
    {
        // A simulated offloading device requests GET_ROWS. The actual scheduler
        // must select the bounded CPU path for a 1.27 GB source key, while its
        // ordinary resident-host control still selects the offloading device.
        ggml_backend_device device=*backend->device;
        device.iface.get_type=[](ggml_backend_dev_t){return GGML_BACKEND_DEVICE_TYPE_GPU;};
        device.iface.supports_op=[](ggml_backend_dev_t,const ggml_tensor *){return true;};
        ggml_backend_buffer_type buffer_type=*ggml_backend_cpu_buffer_type();
        buffer_type.device=&device;simulated_buffer=&buffer_type;
        device.iface.get_buffer_type=[](ggml_backend_dev_t){return simulated_buffer;};
        device.iface.supports_buft=[](ggml_backend_dev_t,ggml_backend_buffer_type_t b){return b==simulated_buffer;};
        device.iface.offload_op=[](ggml_backend_dev_t,const ggml_tensor *){return true;};
        ggml_backend simulated=*backend;simulated.device=&device;
        ggml_backend_t backends[]={&simulated,backend};
        auto selection=ggml_backend_sched_new(backends,nullptr,2,64,false,true);check(selection);
        auto ctx=ggml_init({ggml_tensor_overhead()*8,nullptr,true});check(ctx);
        auto weights=ggml_new_tensor_2d(ctx,GGML_TYPE_BF16,2560,248320);
        auto ids=ggml_new_tensor_1d(ctx,GGML_TYPE_I32,1);
        auto rows=ggml_get_rows(ctx,weights,ids);
        void * key=reinterpret_cast<void *>(0x8000000000ull);
        auto storage=ggml_backend_cpu_buffer_from_ptr(key,ggml_nbytes(weights));check(storage);
        ggml_backend_buffer_set_usage(storage,GGML_BACKEND_BUFFER_USAGE_WEIGHTS);
        weights->data=key;weights->buffer=storage;
        check(ggml_backend_sched_backend_id_from_cur(selection,rows)==0);
        source_key=key;
        check(ggml_backend_sched_backend_id_from_cur(selection,rows)==1);
        source_key=nullptr;
        ggml_backend_buffer_free(storage);ggml_free(ctx);ggml_backend_sched_free(selection);
        simulated_buffer=nullptr;
    }
    auto sched=ggml_backend_sched_new(&backend,nullptr,1,model_capacity,false,true);check(sched);
    check(sched->context_buffer_size==qwen_app_scheduler_context_budget);
    for(int run=0;run<3;run++) {
        auto ctx=ggml_init({ggml_tensor_overhead()*8001+ggml_graph_overhead_custom(8192,false),nullptr,true});check(ctx);
        auto input=ggml_new_tensor_1d(ctx,GGML_TYPE_F32,16);ggml_set_input(input);
        auto output=input;
        for(int n=0;n<7184;n++)output=ggml_scale(ctx,output,1.0f);
        ggml_set_output(output);
        auto graph=ggml_new_graph_custom(ctx,8192,false);ggml_build_forward_expand(graph,output);
        check(graph->n_nodes==7184);
        check(ggml_backend_sched_alloc_graph(sched,graph));
        float values[16];for(int i=0;i<16;i++)values[i]=float(i)+0.25f;
        ggml_backend_tensor_set(input,values,0,sizeof(values));
        check(ggml_backend_sched_graph_compute(sched,graph)==GGML_STATUS_SUCCESS);
        ggml_backend_sched_synchronize(sched);
        float actual[16];ggml_backend_tensor_get(output,actual,0,sizeof(actual));
        for(int i=0;i<16;i++)check(std::isfinite(actual[i])&&actual[i]==values[i]);
        ggml_backend_sched_reset(sched);ggml_free(ctx);
    }
    ggml_backend_sched_free(sched);ggml_backend_free(backend);
    std::cout<<"{\"actual_scheduler\":\"passed\",\"original_context_bytes\":"<<original
        <<",\"bounded_context_bytes\":"<<qwen_app_scheduler_context_budget<<",\"required_7184_bytes\":"<<measured
        <<",\"metadata_allocator_used_bytes\":"<<used<<",\"complete_graph_nodes\":7184,\"CPU_graphs\":3,\"compared_values\":48,\"protected_row_selection\":\"passed\",\"ordinary_offload_control\":\"passed\",\"GPU_calls\":0}"<<std::endl;
}
