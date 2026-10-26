// SPDX-License-Identifier: MIT
// Metadata API stubs plus mechanically extracted actual GGML allocation code.
// Reserve inaccessible host addresses; never commit/read model-sized memory.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-alloc.h"
#include "padded_bank.h"
#include <nlohmann/json.hpp>
#include <array>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#undef GGML_ASSERT
#undef GGML_ABORT
#define GGML_ASSERT(x) do {if(!(x))throw std::runtime_error("Extracted GGML assertion failed");}while(0)
#define GGML_ABORT(...) throw std::runtime_error("Extracted GGML allocation aborted")
#define GGML_LOG_ERROR(...) ((void)0)
using Json=nlohmann::json;
using namespace qwen_app;
void check(bool ok,const char *message){if(!ok)throw std::runtime_error(message);}
struct ggml_backend_buffer_type {std::size_t alignment,max_size;};
struct ggml_backend_buffer {void *base;std::size_t size,alignment;};
struct ggml_cgraph {};
struct ggml_context {
    std::vector<ggml_tensor> tensors;std::array<ggml_cgraph,39> graphs;unsigned graph_count=0;
    ggml_context(){tensors.reserve(90);}
};
struct Fixture {
    std::array<ggml_tensor *,3> banks{},inputs{},ids{};
    std::array<std::array<ggml_tensor *,3>,13> outputs{};
    std::array<std::array<ggml_cgraph *,3>,13> graphs{};
};
extern "C" int64_t ggml_blck_size(ggml_type type) {
    check(type==GGML_TYPE_BF16||type==GGML_TYPE_F32||type==GGML_TYPE_I32,"Unsupported host metadata type");return 1;
}
extern "C" size_t ggml_type_size(ggml_type type) {
    (void)ggml_blck_size(type);return type==GGML_TYPE_BF16?2:4;
}
extern "C" size_t ggml_backend_buft_get_alignment(ggml_backend_buffer_type_t t){return t->alignment;}
extern "C" size_t ggml_backend_buft_get_max_size(ggml_backend_buffer_type_t t){return t->max_size;}
extern "C" size_t ggml_backend_buft_get_alloc_size(ggml_backend_buffer_type_t,const ggml_tensor *t){return ggml_nbytes(t);}
extern "C" size_t ggml_backend_buffer_get_alloc_size(ggml_backend_buffer_t,const ggml_tensor *t){return ggml_nbytes(t);}
extern "C" size_t ggml_backend_buffer_get_size(ggml_backend_buffer_t b){return b->size;}
extern "C" void *ggml_backend_buffer_get_base(ggml_backend_buffer_t b){return b->base;}
extern "C" size_t ggml_backend_buffer_get_alignment(ggml_backend_buffer_t b){return b->alignment;}
extern "C" ggml_status ggml_backend_tensor_alloc(ggml_backend_buffer_t b,ggml_tensor *t,void *address) {
    const auto offset=static_cast<unsigned char *>(address)-static_cast<unsigned char *>(b->base);
    check(offset>=0&&std::size_t(offset)<=b->size&&ggml_nbytes(t)<=b->size-offset,"Host metadata allocation escaped its owner");
    t->data=address;t->buffer=b;return GGML_STATUS_SUCCESS;
}
extern "C" ggml_tensor *ggml_new_tensor_3d(ggml_context *ctx,ggml_type type,int64_t a,int64_t b,int64_t c) {
    check(ctx->tensors.size()<90,"Host metadata tensor bound exceeded");ctx->tensors.emplace_back();auto *t=&ctx->tensors.back();
    t->type=type;t->ne[0]=a;t->ne[1]=b;t->ne[2]=c;t->ne[3]=1;t->nb[0]=ggml_type_size(type);
    for(unsigned i=1;i<4;++i)t->nb[i]=t->nb[i-1]*t->ne[i-1];return t;
}
extern "C" ggml_tensor *ggml_new_tensor_2d(ggml_context *ctx,ggml_type type,int64_t a,int64_t b){return ggml_new_tensor_3d(ctx,type,a,b,1);}
extern "C" void ggml_set_input(ggml_tensor *){}
extern "C" void ggml_set_output(ggml_tensor *){}
extern "C" ggml_tensor *ggml_view_3d(ggml_context *ctx,ggml_tensor *root,int64_t a,int64_t b,int64_t c,size_t nb1,size_t nb2,size_t offset) {
    auto *t=ggml_new_tensor_3d(ctx,root->type,a,b,c);t->nb[1]=nb1;t->nb[2]=nb2;t->nb[3]=nb2*c;t->view_src=root;t->view_offs=offset;return t;
}
extern "C" ggml_tensor *ggml_mul_mat_id(ggml_context *ctx,ggml_tensor *a,ggml_tensor *,ggml_tensor *ids) {
    // Fixed admitted metadata geometry, not a host implementation of GEMV.
    return ggml_new_tensor_3d(ctx,GGML_TYPE_F32,a->ne[1],ids->ne[0],1);
}
extern "C" ggml_cgraph *ggml_new_graph_custom(ggml_context *ctx,size_t size,bool gradients) {
    check(size==16&&!gradients&&ctx->graph_count<39,"Host graph bound exceeded");return &ctx->graphs[ctx->graph_count++];
}
extern "C" void ggml_build_forward_expand(ggml_cgraph *,ggml_tensor *){}

#include "actual_bank_allocation.inc"

int main(int argc,char **argv) {
    if(argc!=2)return 2;std::ifstream file(argv[1]);const auto policy=Json::parse(file).at("native_vector_bank_validation");
    Json result=Json::array();
    for(const auto alignment:{1u,2u,4u,8u,16u,32u}) {
        Json observed=Json::array();std::size_t original_size=0;
        for(unsigned candidate=0;candidate<2;++candidate) {
            ggml_context context;Fixture fixture;
            if(candidate)build_candidate(&context,&fixture,policy);else build_failed(&context,&fixture,policy);
            check(context.tensors.size()==87&&context.graph_count==39,"Construction did not match actual fixture metadata");
            std::vector<ggml_tensor *> tensors;for(auto &t:context.tensors)tensors.push_back(&t);
            ggml_backend_buffer_type type{alignment,1u<<30};
            const auto plan=ggml_backend_buft_alloc_buffer_n_plan(&type,tensors.data(),int(tensors.size()));
            check(plan.size()==1&&plan[0].size<=(512u<<20),"Actual GGML plan exceeds its existing cap");
            auto *base=VirtualAlloc(nullptr,512u<<20,MEM_RESERVE,PAGE_NOACCESS);check(base,"Host virtual reservation refused");
            ggml_backend_buffer buffer{base,plan[0].size,alignment};auto allocator=ggml_tallocr_new(&buffer);
            for(auto *t:tensors)if(!t->view_src)check(ggml_tallocr_alloc(&allocator,t)==GGML_STATUS_SUCCESS,"Actual tensor allocator failed");
            std::array<std::size_t,3> offsets{};
            for(unsigned role=0;role<3;++role)offsets[role]=static_cast<unsigned char *>(fixture.banks[role]->data)-static_cast<unsigned char *>(base);
            if(candidate) {
                check(plan[0].size==original_size,"Alignment correction added payload bytes");
                for(auto offset:offsets)check(offset%16384==0,"A corrected bank remains unaligned");
            }else{original_size=plan[0].size;check(offsets[0]%16384==0&&offsets[1]%16384!=0,"Failed fixture refusal was not reproduced");}
            observed.push_back({{"candidate",bool(candidate)},{"bank_offsets",offsets},{"payload_bytes",plan[0].size}});
            check(VirtualFree(base,0,MEM_RELEASE)!=0,"Host virtual reservation release failed");
        }
        result.push_back({{"descriptor_alignment",alignment},{"arms",observed}});
    }
    std::cout<<Json({{"actual_allocation_functions",true},{"actual_fixture_construction_extracted",true},
        {"failed_layout_reproduced",true},{"corrected_banks_aligned",true},{"physical_weight_bytes_allocated",0},
        {"GPU_calls",0},{"learned_inference",false},{"controls",result}})<<std::endl;
}
