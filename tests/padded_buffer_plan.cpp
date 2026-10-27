// SPDX-License-Identifier: MIT
#include "padded_cache_geometry.h"
#include "ggml.h"
#include "ggml-backend.h"
#include <iostream>
#include <vector>
static std::size_t actual_limit=2ull<<30;
extern "C" std::size_t ggml_backend_buft_get_alignment(ggml_backend_buffer_type_t){return 16384;}
extern "C" std::size_t ggml_backend_buft_get_max_size(ggml_backend_buffer_type_t){
    return qwen_app::selected_padded_buffer_batch_limit(actual_limit,true);
}
extern "C" std::size_t ggml_backend_buft_get_alloc_size(ggml_backend_buffer_type_t,const ggml_tensor *){
    return qwen_app::selected_padded_cache_geometry().tensor_bytes();
}
// Verbatim pinned upstream packing planner, extracted by the manual checker.
#include "actual_padded_buffer_plan.inc"
static void check(bool v){if(!v)throw std::runtime_error("Padded buffer packing control failed");}
int main(int argc,char **argv){
    if(argc==2&&std::string(argv[1])=="--large")qwen_app::select_experimental_padded_cache_128();
    else if(argc!=1)throw std::invalid_argument("Unknown buffer packing test scope");
    ggml_tensor banks[3]{},views[3]{};ggml_tensor *tensors[6]{};
    for(unsigned i=0;i<3;++i){views[i].view_src=&banks[i];tensors[2*i]=&banks[i];tensors[2*i+1]=&views[i];}
    const auto plan=ggml_backend_buft_alloc_buffer_n_plan(nullptr,tensors,6);
    const auto geometry=qwen_app::selected_padded_cache_geometry();
    check(plan.size()==(geometry.active_slots==128?3:1));
    std::size_t total=0;
    for(const auto &item:plan){check(item.size>0&&item.size<=(512ull<<20));total+=item.size;}
    check(total==3*geometry.tensor_bytes());
    if(geometry.active_slots==128) {
        for(unsigned i=0;i<3;++i)check(plan[i].first==int(2*i)&&plan[i].last==int(2*i+2));
    }
    actual_limit=128u<<20;check(ggml_backend_buft_get_max_size(nullptr)==actual_limit);
    std::cout<<"Actual upstream planner kept views uncharged and banks within the retained per-buffer cap\n";
}
