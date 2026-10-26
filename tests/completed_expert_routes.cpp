// SPDX-License-Identifier: MIT
// Real GGML CPU downloads with the native observer; no learned model or GPU.
#include "completed_expert_routes.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-cpu.h"
#include <array>
#include <atomic>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

extern "C" void __wrap_ggml_backend_tensor_get_async(ggml_backend_t,const ggml_tensor *,void *,size_t,size_t);
extern "C" void __wrap_ggml_backend_synchronize(ggml_backend_t);
static std::atomic<unsigned> get_calls{0},syncs{0};
static std::string scenario;
static bool exercise=false;
extern "C" void __real_ggml_backend_tensor_get_async(ggml_backend_t backend,const ggml_tensor * tensor,void * target,size_t offset,size_t bytes) {
    ++get_calls;
    if(exercise&&scenario=="get_failure")throw std::runtime_error("Synthetic GET failure");
    if(exercise&&scenario=="internal_sync")__wrap_ggml_backend_synchronize(backend);
    ggml_backend_tensor_get_async(backend,tensor,target,offset,bytes);
}
extern "C" void __real_ggml_backend_synchronize(ggml_backend_t backend) {
    ++syncs;
    if(exercise&&scenario=="sync_failure")throw std::runtime_error("Synthetic synchronization failure");
    ggml_backend_synchronize(backend);
}
static void check(bool value){if(!value)throw std::runtime_error("Completed route observer invariant failed");}
template<class F>static void rejected(F f){bool caught=false;try{f();}catch(const std::runtime_error&){caught=true;}check(caught);}
int main(int argc,char ** argv) {
    check(argc==2);scenario=argv[1];
    auto backend=ggml_backend_cpu_init();check(backend);ggml_backend_cpu_set_n_threads(backend,1);
    auto other=ggml_backend_cpu_init();check(other);ggml_backend_cpu_set_n_threads(other,1);
    const int width=scenario=="width8"?8:scenario=="width4"?4:scenario=="width3"?3:2;
    auto context=ggml_init({16*ggml_tensor_overhead(),nullptr,true});check(context);
    auto logits=ggml_new_tensor_2d(context,GGML_TYPE_F32,512,width);check(logits);
    auto selected=ggml_argsort_top_k(context,logits,10);check(selected);
    ggml_set_name(selected,"ffn_moe_topk-0");
    auto contiguous=ggml_is_contiguous(selected)?selected:ggml_cont(context,selected);
    auto tensor=ggml_reshape_1d(context,contiguous,ggml_nelements(contiguous));check(tensor);
    auto buffer=ggml_backend_alloc_ctx_tensors(context,backend);check(buffer);
    std::array<std::int32_t,80> input{},target{};
    for(int i=0;i<10*width;++i)input[i]=(i*17)%512;
    if(scenario=="negative_id")input[0]=-1;
    if(scenario=="large_id")input[0]=512;
    ggml_backend_tensor_set(tensor,input.data(),0,ggml_nbytes(tensor));
    ggml_set_name(tensor,"unrelated");
    __wrap_ggml_backend_tensor_get_async(backend,tensor,target.data(),0,ggml_nbytes(tensor));
    __wrap_ggml_backend_synchronize(backend);check(get_calls==1&&syncs==1);get_calls=0;syncs=0;
    qwen_app::begin_completed_expert_routes();
    exercise=true;
    if(scenario.rfind("range_",0)==0) {
        check(qwen_app::completed_expert_route_cursor()==0);
        for(unsigned row=0;row<96;++row) {
            if(row==48&&scenario=="range_mismatch"){++input[0];ggml_backend_tensor_set(tensor,input.data(),0,ggml_nbytes(tensor));}
            ggml_format_name(tensor,"ffn_moe_topk-%u (cont) (reshaped)",row%48);
            __wrap_ggml_backend_tensor_get_async(backend,tensor,target.data(),0,ggml_nbytes(tensor));
            __wrap_ggml_backend_synchronize(backend);
        }
        check(qwen_app::completed_expert_route_cursor()==96);
        if(scenario=="range_equal") {
            qwen_app::compare_completed_expert_route_ranges(0,48,48);
            qwen_app::compare_completed_expert_route_ranges(96,96,0);
            check(qwen_app::finish_completed_expert_routes(2).size()==96);
        }else {
            if(scenario=="range_bounds")rejected([]{qwen_app::compare_completed_expert_route_ranges(48,96,48);});
            else if(scenario=="range_mismatch")rejected([]{qwen_app::compare_completed_expert_route_ranges(0,48,48);});
            else if(scenario=="range_wrong_owner") {
                std::atomic<bool> refused{false};std::thread child([&]{try{qwen_app::completed_expert_route_cursor();}catch(...){refused=true;}});child.join();check(refused);
            }else if(scenario=="range_pending") {
                ggml_set_name(tensor,"ffn_moe_topk-0 (cont) (reshaped)");
                __wrap_ggml_backend_tensor_get_async(backend,tensor,target.data(),0,ggml_nbytes(tensor));
                rejected([]{qwen_app::completed_expert_route_cursor();});
                __wrap_ggml_backend_synchronize(backend);
            }else throw std::runtime_error("Unknown range control");
            check(qwen_app::completed_expert_routes_pending());rejected([]{qwen_app::finish_completed_expert_routes(2);});
        }
    }else if(scenario=="begin_twice") {
        rejected([]{qwen_app::begin_completed_expert_routes();});check(get_calls==0);
    }else {
        const bool positive=scenario=="positive"||scenario=="width3"||scenario=="width4"||scenario=="internal_sync"||scenario=="other_thread_sync"||scenario=="other_backend_sync"||scenario=="retained_batches";
        const unsigned total=scenario=="overflow"?qwen_app::expert_route_capacity+1:positive||scenario=="finish_mismatch"?48:1;
        bool failed=false;
        for(unsigned row=0;row<total;++row) {
            const auto layer=scenario=="bad_layer"?48:scenario=="wrong_order"?1:row%48;
            ggml_format_name(selected,"ffn_moe_topk-%u",layer);
            if(contiguous!=selected)ggml_format_name(contiguous,"%s (cont)",ggml_get_name(selected));
            ggml_format_name(tensor,"%s (reshaped)",ggml_get_name(contiguous));
            try {
                if(scenario=="other_thread_get"){
                    std::atomic<bool> returned{false};
                    std::thread child([&]{__wrap_ggml_backend_tensor_get_async(backend,tensor,target.data(),0,ggml_nbytes(tensor));returned=true;});
                    child.join();check(returned&&qwen_app::completed_expert_routes_pending());
                    __wrap_ggml_backend_synchronize(backend);
                    throw std::runtime_error("Observed expected capture-only cross-producer refusal");
                }
                __wrap_ggml_backend_tensor_get_async(backend,tensor,target.data(),0,
                    ggml_nbytes(tensor)-(scenario=="bad_count"?4:0));
                check(qwen_app::completed_expert_routes_pending());
                if(scenario=="finish_pending")qwen_app::finish_completed_expert_routes(1);
                if(scenario=="duplicate_get")__wrap_ggml_backend_tensor_get_async(backend,tensor,target.data(),0,ggml_nbytes(tensor));
                if(scenario=="other_thread_sync"){
                    std::thread child([&]{__wrap_ggml_backend_synchronize(backend);});child.join();
                    check(qwen_app::completed_expert_routes_pending());
                }
                if(scenario=="other_backend_sync"){
                    __wrap_ggml_backend_synchronize(other);check(qwen_app::completed_expert_routes_pending());
                }
                __wrap_ggml_backend_synchronize(backend);
                check(!qwen_app::completed_expert_routes_pending());
            }catch(const std::runtime_error&){failed=true;break;}
        }
        if(positive){
            check(!failed);auto rows=qwen_app::finish_completed_expert_routes(1);check(rows.size()==48);
            check(rows.capacity()==rows.size());
            for(unsigned i=0;i<48;++i){check(rows[i].layer==i&&rows[i].tokens==width);for(int j=0;j<10*width;++j)check(rows[i].ids[j]==input[j]);}
            check(!qwen_app::completed_expert_routes_pending());
            if(scenario=="retained_batches"){
                const auto original=input;
                std::vector<std::vector<qwen_app::CompletedExpertRoute>> retained;
                retained.push_back(std::move(rows));
                for(unsigned batch=1;batch<3;++batch){
                    qwen_app::begin_completed_expert_routes();
                    for(int j=0;j<10*width;++j)input[j]=(original[j]+batch)%512;
                    ggml_backend_tensor_set(tensor,input.data(),0,ggml_nbytes(tensor));
                    for(unsigned layer=0;layer<48;++layer){
                        ggml_format_name(tensor,"ffn_moe_topk-%u (cont) (reshaped)",layer);
                        __wrap_ggml_backend_tensor_get_async(backend,tensor,target.data(),0,ggml_nbytes(tensor));
                        __wrap_ggml_backend_synchronize(backend);
                    }
                    auto next=qwen_app::finish_completed_expert_routes(1);check(next.size()==48&&next.capacity()==48);
                    retained.push_back(std::move(next));
                }
                for(unsigned batch=0;batch<3;++batch)for(const auto & row:retained[batch])
                    for(int j=0;j<10*width;++j)check(row.ids[j]==unsigned((original[j]+batch)%512));
                check(get_calls==144&&syncs==144&&!qwen_app::completed_expert_routes_pending());
            }
        }else {
            if(scenario=="finish_mismatch")check(!failed);else check(failed);
            rejected([&]{qwen_app::finish_completed_expert_routes(scenario=="finish_mismatch"?2:1);});
            check(qwen_app::completed_expert_routes_pending());
            rejected([]{qwen_app::begin_completed_expert_routes();});
            if(scenario=="overflow")check(get_calls==qwen_app::expert_route_capacity+1);
            if(scenario=="duplicate_get")check(get_calls==2);
            if(scenario=="finish_pending")check(get_calls==1);
            if(scenario=="bad_layer"||scenario=="wrong_order"||scenario=="bad_count"||scenario=="width8"||scenario=="other_thread_get")check(get_calls==1);
            // A metadata-only refusal must not alter a later original call.
            // Never retry a real provider failure or an unsynchronized GET.
            if(scenario!="get_failure"&&scenario!="sync_failure"&&scenario!="finish_pending"){
                const auto previous=get_calls.load();ggml_set_name(tensor,"unrelated");
                __wrap_ggml_backend_tensor_get_async(backend,tensor,target.data(),0,ggml_nbytes(tensor));
                __wrap_ggml_backend_synchronize(backend);check(get_calls==previous+1);
            }
        }
    }
    ggml_backend_buffer_free(buffer);ggml_free(context);ggml_backend_free(other);ggml_backend_free(backend);
    std::cout<<"{\"scenario\":\""<<scenario<<"\",\"passed\":true,\"forwarded_original_CPU_download_calls\":"<<get_calls
        <<",\"forwarded_original_CPU_sync_calls\":"<<syncs<<",\"GPU_calls\":0,\"learned_model_inference\":false}"<<std::endl;
}
