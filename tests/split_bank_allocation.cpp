// SPDX-License-Identifier: MIT
// Actual allocation owner with metadata API stubs and inaccessible host VA.
// This executes no tensor arithmetic, file I/O or GPU command.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "split_bank_allocation.h"
#include "padded_cache_geometry.h"
#include "native_gpu.h"
#include "system_memory.h"
#include "ggml-alloc.h"
#include "ggml-vulkan.h"
#include <iostream>
#include <cassert>
#include <string>
#include <vector>
#undef GGML_ASSERT
#undef GGML_ABORT
#define GGML_ASSERT(x) do{if(!(x))throw std::runtime_error("Actual planner assertion failed");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Actual planner aborted")
#define GGML_LOG_ERROR(...) ((void)0)
static std::string scenario;
static unsigned plans=0,allocations=0,frees=0,context_frees=0,retains=0,uses=0,depth=0,checkpoints=0;
static std::size_t alignment=32;
static void check(bool ok){if(!ok)throw std::runtime_error("Split allocation lifetime control failed");}
struct ggml_context {std::vector<ggml_tensor> tensors;ggml_context(){tensors.reserve(8);}};
struct ggml_backend {bool Vulkan=true;};
struct ggml_backend_buffer_type {};
struct ggml_backend_buffer {void *base,*reservation;std::size_t size;std::uint64_t owner;};
static ggml_backend_buffer_type type;
static ggml_backend_buffer *first_buffer=nullptr;
extern "C" std::int64_t ggml_blck_size(ggml_type t){check(t==GGML_TYPE_BF16);return 1;}
extern "C" std::size_t ggml_type_size(ggml_type t){check(t==GGML_TYPE_BF16);return 2;}
extern "C" std::size_t ggml_backend_buft_get_alignment(ggml_backend_buffer_type_t){return alignment;}
extern "C" std::size_t ggml_backend_buft_get_max_size(ggml_backend_buffer_type_t){return 512u<<20;}
extern "C" std::size_t ggml_backend_buft_get_alloc_size(ggml_backend_buffer_type_t,const ggml_tensor *t){return ggml_nbytes(t);}
extern "C" std::size_t ggml_backend_buffer_get_alloc_size(ggml_backend_buffer_t,const ggml_tensor *t){return ggml_nbytes(t);}
extern "C" std::size_t ggml_backend_buffer_get_size(ggml_backend_buffer_t b){return b->size;}
extern "C" std::size_t ggml_backend_buffer_get_alignment(ggml_backend_buffer_t){return alignment;}
extern "C" void *ggml_backend_buffer_get_base(ggml_backend_buffer_t b){return b->base;}
extern "C" ggml_status ggml_backend_tensor_alloc(ggml_backend_buffer_t b,ggml_tensor *t,void *p){t->data=p;t->buffer=b;return GGML_STATUS_SUCCESS;}
// Verbatim pinned nbytes, packing plan and tallocr implementation.
#include "actual_split_allocation.inc"
extern "C" std::size_t ggml_tensor_overhead(){return sizeof(ggml_tensor)+64;}
extern "C" ggml_context *ggml_init(ggml_init_params p){check(p.no_alloc&&p.mem_size>=sizeof(ggml_tensor)*3);return new ggml_context;}
extern "C" void ggml_free(ggml_context *c){++context_frees;delete c;}
extern "C" ggml_tensor *ggml_new_tensor_1d(ggml_context *c,ggml_type t,std::int64_t n){
    check(c->tensors.size()<8);c->tensors.emplace_back();auto *x=&c->tensors.back();x->type=t;
    x->ne[0]=n;for(unsigned i=1;i<4;++i)x->ne[i]=1;
    x->nb[0]=2;for(unsigned i=1;i<4;++i)x->nb[i]=x->nb[i-1]*x->ne[i-1];return x;
}
extern "C" void ggml_set_input(ggml_tensor *){}
extern "C" bool ggml_backend_is_vk(ggml_backend_t b){return b->Vulkan;}
extern "C" ggml_backend_buffer_type_t ggml_backend_get_default_buffer_type(ggml_backend_t){return &type;}
extern "C" std::size_t ggml_backend_alloc_ctx_tensors_from_buft_size(ggml_context *c,ggml_backend_buffer_type_t b){
    ++plans;std::vector<ggml_tensor *> tensors;for(auto &t:c->tensors)tensors.push_back(&t);
    const auto plan=ggml_backend_buft_alloc_buffer_n_plan(b,tensors.data(),int(tensors.size()));check(plan.size()==1);return plan[0].size;
}
extern "C" ggml_backend_buffer_t ggml_backend_alloc_ctx_tensors(ggml_context *c,ggml_backend_t){
    check(plans==2);++allocations;
    if(scenario=="second-allocation-failed"&&allocations==2)return nullptr;
    std::vector<ggml_tensor *> tensors;for(auto &t:c->tensors)tensors.push_back(&t);
    const auto plan=ggml_backend_buft_alloc_buffer_n_plan(&type,tensors.data(),int(tensors.size()));check(plan.size()==1);
    auto *base=VirtualAlloc(nullptr,256u<<20,MEM_RESERVE,PAGE_NOACCESS);check(base!=nullptr);
    auto *b=new ggml_backend_buffer{base,base,plan[0].size,allocations};
    if(scenario=="aliased-allocation"&&allocations==2)b->owner=1;
    if(scenario=="overlapping-addresses"&&allocations==2)b->base=first_buffer->base;
    if(allocations==1)first_buffer=b;
    auto allocator=ggml_tallocr_new(b);for(auto &t:c->tensors)check(ggml_tallocr_alloc(&allocator,&t)==GGML_STATUS_SUCCESS);
    return b;
}
extern "C" void ggml_backend_buffer_free(ggml_backend_buffer_t b){check(!depth);++frees;check(VirtualFree(b->reservation,0,MEM_RELEASE)!=0);delete b;}
extern "C" void ggml_backend_synchronize(ggml_backend_t){}
extern "C" void qwen_native_driver_checkpoint(){++checkpoints;if(scenario=="checkpoint-failed")throw std::runtime_error("Uncertain completion");}
extern "C" void qwen_native_driver_retain(){++retains;}
namespace qwen_app {SystemMemoryObservation admit_native_system_memory(){return {64u<<20,16384,138739,8192,898,2974,206};}}
extern "C" int ggml_app_vk_probe_owned_split_bank(ggml_tensor *t,unsigned group,int (*use)(const qwen_app::SplitBankLease &,void *),void *opaque){
    check(group<2&&t->buffer);auto *b=t->buffer;
    qwen_app::SplitBankLease grant{t->data,ggml_nbytes(t),alignment,7,b->owner};
    if(scenario=="missing-coherency")grant.memory_flags=3;
    if(scenario=="invalid-descriptor")grant.descriptor_alignment=3;
    ++depth;try{const auto result=use(grant,opaque);--depth;return result;}catch(...){--depth;throw;}
}
static int use_banks(const qwen_app::SplitBankBackings &b,const qwen_app::SplitBankRoots &r,void *opaque){
    ++uses;check(depth==6&&allocations==2&&frees==0);const auto owners=qwen_app::validate_split_bank_backings(b);
    check(owners[0][0]!=owners[1][0]&&r[0][0]->buffer==r[0][2]->buffer&&r[0][0]->buffer!=r[1][0]->buffer);
    if(scenario=="unknown-use")throw std::runtime_error("Read or GPU completion unknown");
    if(scenario=="returned-ineligible")return 1;
    if(scenario=="reentrant"){
        auto *owner=static_cast<qwen_app::SplitBankAllocation *>(opaque);bool refused=false;
        try{owner->with_owned_backings(use_banks,opaque);}catch(const std::invalid_argument&){refused=true;}check(refused);
    }
    return 0;
}
int main(int argc,char **argv){try{
    if(argc!=2)return 2;scenario=argv[1];ggml_backend backend;
    if(scenario=="coarse-alignment")alignment=2u<<20;
    if(scenario=="CPU-backend")backend.Vulkan=false;
    if(scenario=="cache128")qwen_app::select_experimental_padded_cache_128();
    qwen_app::SplitBankAllocation owner;bool failure=false;
    try{owner.prepare(&backend);owner.with_owned_backings(use_banks,&owner);}catch(const std::exception&){failure=true;}
    const bool positive=scenario=="positive"||scenario=="reentrant"||scenario=="wrong-thread";
    check(failure!=positive);
    if(positive){
        if(scenario=="wrong-thread"){bool refused=false;std::thread t([&]{try{owner.close_completed();}catch(const std::logic_error&){refused=true;}});t.join();check(refused&&frees==0);}
        check(owner.charged_bytes()==512u<<20&&uses==1&&checkpoints>0);owner.close_completed();check(frees==2&&context_frees==2&&retains==0);
        bool refused=false;try{owner.close_completed();}catch(const std::invalid_argument&){refused=true;}check(refused&&frees==2);
    }else{bool refused=false;try{owner.close_completed();}catch(const std::invalid_argument&){refused=true;}check(refused&&frees==0);
        if(scenario=="CPU-backend"||scenario=="cache128"||scenario=="coarse-alignment")check(allocations==0);
        if(scenario=="aliased-allocation"||scenario=="overlapping-addresses"||scenario=="missing-coherency"||scenario=="invalid-descriptor")check(uses==0);
        if(scenario=="unknown-use"||scenario=="returned-ineligible")check(uses==1&&retains==1);
    }
    std::cout<<"{\"passed\":true,\"metadata_API_harness\":true,\"physical_weight_bytes\":0,\"GPU_calls\":0}"<<'\n';
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
