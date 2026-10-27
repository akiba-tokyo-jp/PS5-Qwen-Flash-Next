// SPDX-License-Identifier: MIT
#include "split_bank_route.h"
#include "padded_bank_layout.h"
#include "indexed_vector.h"
#include "ggml-backend.h"
#include <iostream>
extern "C" bool qwen_app_padded_index_layout(const ggml_tensor *);
using namespace qwen_app;
#define check(good) do {if(!(good))throw std::runtime_error("Split route control failed at line "+std::to_string(__LINE__)+": " #good);} while(false)
int main() {
    auto *ctx=ggml_init({ggml_tensor_overhead()*12000,nullptr,true});check(ctx);
    unsigned accepted=0,refused=0,default_refusals=0;
    const auto reject=[&](ggml_tensor *out){check(!split_bank_indexed_vector_layout(out,32));++refused;};
    for(unsigned group=0;group<2;++group)for(unsigned down=0;down<2;++down)for(unsigned count=1;count<=10;++count)for(unsigned expanded=0;expanded<2;++expanded) {
        auto *root=ggml_new_tensor_1d(ctx,GGML_TYPE_BF16,split_bank_planes[0]*padded_bank_stride/2);
        root->buffer=reinterpret_cast<ggml_backend_buffer_t>(std::uintptr_t(1));root->data=reinterpret_cast<void *>(std::uintptr_t(0x10000000000ull));
        const auto k=down?640:2560,n=down?2560:640,residue=down?1632:2784;
        auto *a=ggml_view_3d(ctx,root,k,n,split_bank_active[group],k*2,padded_bank_stride,residue);
        a->buffer=root->buffer; // Metadata seam for the allocator's view binding.
        auto *b=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,k,expanded?count:1,1),*ids=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,count,1);
        auto *out=ggml_mul_mat_id(ctx,a,b,ids);
        check(split_bank_indexed_vector_layout(out,32));++accepted;
        check(!bf16_indexed_vector_layout(out));
        check(!qwen_app_padded_index_layout(out));++default_refusals;
        configure_split_index_layout(true,32);check(qwen_app_padded_index_layout(out));configure_split_index_layout(false);
        const auto original_a=*a,original_b=*b,original_ids=*ids,original_out=*out,original_root=*root;
        a->type=GGML_TYPE_F16;reject(out);*a=original_a;
        a->view_offs=bank_read_alignment;reject(out);*a=original_a;
        a->view_offs=1;reject(out);*a=original_a;
        a->nb[2]-=32;reject(out);*a=original_a;
        a->nb[3]-=32;reject(out);*a=original_a;
        a->ne[2]=28;reject(out);*a=original_a;
        a->buffer=nullptr;reject(out);*a=original_a;
        a->buffer=reinterpret_cast<ggml_backend_buffer_t>(std::uintptr_t(2));reject(out);*a=original_a;
        root->view_src=a;reject(out);*root=original_root;
        root->ne[0]-=16384;reject(out);*root=original_root;
        b->type=GGML_TYPE_F16;reject(out);*b=original_b;
        b->ne[2]=2;reject(out);*b=original_b;
        b->nb[1]+=4;reject(out);*b=original_b;
        ids->ne[0]=11;reject(out);*ids=original_ids;
        ids->type=GGML_TYPE_F32;reject(out);*ids=original_ids;
        out->ne[1]++;reject(out);*out=original_out;
        out->nb[1]+=4;reject(out);*out=original_out;
        out->src[2]=nullptr;reject(out);*out=original_out;
        check(!split_bank_indexed_vector_layout(out,0)&&!split_bank_indexed_vector_layout(out,3));refused+=2;
    }
    configure_padded_index_layout(true,32);
    // The original production root remains eligible only through its original
    // policy, including after experimental split enable/disable.
    auto *root=ggml_new_tensor_3d(ctx,GGML_TYPE_BF16,2560,640,54);root->nb[2]=padded_bank_stride;root->nb[3]=54*padded_bank_stride;
    root->buffer=reinterpret_cast<ggml_backend_buffer_t>(std::uintptr_t(1));root->data=reinterpret_cast<void *>(std::uintptr_t(0x10000000000ull));
    auto *view=ggml_view_3d(ctx,root,2560,640,53,5120,padded_bank_stride,2784);
    view->buffer=root->buffer;
    auto *x=ggml_new_tensor_3d(ctx,GGML_TYPE_F32,2560,1,1),*ids=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,10,1);
    auto *out=ggml_mul_mat_id(ctx,view,x,ids);check(qwen_app_padded_index_layout(out));
    configure_split_index_layout(true,32);check(qwen_app_padded_index_layout(out));configure_split_index_layout(false);check(qwen_app_padded_index_layout(out));
    configure_padded_index_layout(false);check(!qwen_app_padded_index_layout(out));ggml_free(ctx);
    std::cout<<"{\"actual_GGML_partial_shapes\":"<<accepted<<",\"altered_layout_refusals\":"<<refused
        <<",\"experimental_default_off_refusals\":"<<default_refusals<<",\"original_production_route_preserved\":true,\"PS5_operations\":0,\"GPU_calls\":0}\n";
}
