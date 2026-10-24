// SPDX-License-Identifier: MIT
// Execute the pinned allocator's planning code with storage-free metadata.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include "nlohmann/json.hpp"

struct ggml_tensor { void *data=nullptr; ggml_tensor *view_src=nullptr; std::size_t bytes=0; };
struct SyntheticBufferType { std::size_t alignment=256, target=1ull<<30; };
using ggml_backend_buffer_type_t=SyntheticBufferType *;
static std::size_t ggml_backend_buft_get_alignment(SyntheticBufferType *value) { return value->alignment; }
static std::size_t ggml_backend_buft_get_max_size(SyntheticBufferType *value) { return value->target; }
static std::size_t ggml_backend_buft_get_alloc_size(SyntheticBufferType *,ggml_tensor *value) { return value->bytes; }
#define GGML_PAD(value,alignment) (((value)+(alignment)-1)&~((alignment)-1))
#include "actual-buffer-plan.inc"

static void check(bool value) { if(!value)throw std::runtime_error("Pinned buffer planning check failed"); }
static void replay(std::vector<ggml_tensor> tensors,std::size_t alignment,std::size_t target) {
    SyntheticBufferType type{alignment,target}; std::vector<ggml_tensor *> pointers;
    std::size_t expected=0;
    for(auto &tensor:tensors) {
        pointers.push_back(&tensor); expected+=GGML_PAD(tensor.bytes,alignment);
        check(GGML_PAD(tensor.bytes,alignment)<=target);
    }
    const auto plan=ggml_backend_buft_alloc_buffer_n_plan(&type,pointers.data(),int(pointers.size()));
    std::size_t sum=0; int next=0;
    for(const auto &part:plan) {
        check(part.size>0&&part.size<=target&&part.first==next&&part.last>part.first&&part.last<=int(tensors.size()));
        std::size_t actual=0;
        for(int i=part.first;i<part.last;++i)actual+=GGML_PAD(tensors[i].bytes,alignment);
        check(actual==part.size);sum+=part.size;next=part.last;
    }
    check(sum==expected&&next==int(tensors.size()));
}

int main(int argc,char **argv) {
    try {
        if(argc!=2)throw std::invalid_argument("The complete storage-free metadata plan is required");
        std::ifstream input(argv[1]);nlohmann::json original;input>>original;
        std::vector<ggml_tensor> tensors;std::size_t total=0,largest=0;
        for(const auto &item:original.at("tensors").items()) {
            if(item.value().at("placement")!="device_weights")continue;
            const auto bytes=item.value().at("bytes").get<std::size_t>();
            tensors.push_back({nullptr,nullptr,bytes});total+=bytes;largest=std::max(largest,bytes);
        }
        check(total==8755105280ull&&largest==1271398400ull&&!tensors.empty());
        // Prove why the old comparison with the default batching target was
        // overly restrictive: upstream legitimately emits an oversized tensor.
        SyntheticBufferType default_type;ggml_tensor output{nullptr,nullptr,largest};auto *pointer=&output;
        const auto oversized=ggml_backend_buft_alloc_buffer_n_plan(&default_type,&pointer,1);
        check(oversized.size()==1&&oversized[0].size==largest&&largest>default_type.target);
        unsigned cases=1;
        // Tensor insertion order is determined by the real loader at runtime.
        // These orders prove the size/accounting invariant, not exact BO layout.
        for(auto alignment:{std::size_t(16),std::size_t(256),std::size_t(65536)}) {
            replay(tensors,alignment,2ull<<30);++cases;
            std::reverse(tensors.begin(),tensors.end());replay(tensors,alignment,2ull<<30);++cases;
            std::sort(tensors.begin(),tensors.end(),[](auto a,auto b){return a.bytes<b.bytes;});
            replay(tensors,alignment,2ull<<30);++cases;
            std::reverse(tensors.begin(),tensors.end());replay(tensors,alignment,2ull<<30);++cases;
        }
        std::cout<<nlohmann::json({{"pinned_allocator_plan_cases",cases},{"device_tensor_count",tensors.size()},
            {"device_tensor_bytes",total},{"largest_tensor_bytes",largest},{"requested_batch_target_bytes",2ull<<30},
            {"default_is_soft_batch_target",true},{"all_tested_orders_fit_requested_target",true},
            {"exact_runtime_buffer_layout_qualified",false},{"physical_memory_admitted",false},
            {"console_access",false},{"learned_inference_performed",false}}).dump()<<'\n';
    } catch(const std::exception &error) {std::cerr<<error.what()<<'\n';return 1;}
}
