// SPDX-License-Identifier: MIT
#include "padded_bank_layout.h"
#include "padded_bank_bridge.h"
#include "padded_bank.h"
#include "ggml.h"
#include <array>
#include <stdexcept>
static void require(bool test){if(!test)throw std::runtime_error("Padded bank bounds control failed");}
static ggml_tensor tensor(ggml_type type,std::int64_t k,std::int64_t n,std::int64_t e,std::size_t bytes){
    ggml_tensor t{};t.type=type;t.ne[0]=k;t.ne[1]=n;t.ne[2]=e;t.ne[3]=1;
    t.nb[0]=bytes;t.nb[1]=bytes*k;t.nb[2]=bytes*k*n;t.nb[3]=bytes*k*n*e;return t;
}
int main(){
    using namespace qwen_app;
    require(!qwen_app_padded_index_layout(nullptr));
    for(const bool down:{false,true})for(const unsigned v:{1u,10u}){
        const unsigned k=down?640:2560,n=down?2560:640;
        auto root=tensor(GGML_TYPE_BF16,k,n,54,2);root.nb[2]=padded_bank_stride;root.nb[3]=54*padded_bank_stride;
        auto a=root;a.ne[2]=53;a.view_src=&root;a.nb[3]=53*padded_bank_stride;
        auto b=tensor(GGML_TYPE_F32,k,v,1,4),ids=tensor(GGML_TYPE_I32,10,1,1,4),out=tensor(GGML_TYPE_F32,n,10,1,4);
        root.buffer=a.buffer=reinterpret_cast<ggml_backend_buffer *>(std::uintptr_t(16));
        out.src[0]=&a;out.src[1]=&b;out.src[2]=&ids;
        configure_padded_index_layout(false);require(!qwen_app_padded_index_layout(&out));
        configure_padded_index_layout(true,4);
        for(const auto residue:original_bank_residues){
            a.view_offs=residue;require(qwen_app_padded_index_layout(&out));
            for(unsigned slot=0;slot<53;++slot){
                const auto r=padded_bank_slot(slot,residue,padded_bank_tensor_bytes,4);
                require(r.payload_offset==slot*padded_bank_stride+residue);
                require(r.aligned_write_offset%16384==0&&r.requested_bytes%16384==0);
                require(r.payload_offset+bank_expert_bytes<=r.aligned_write_offset+r.requested_bytes);
                require(r.aligned_write_offset+r.requested_bytes<=53*padded_bank_stride);
            }
        }
        const auto saved_a=a,saved_root=root,saved_b=b;
        a.view_offs=16384;require(!qwen_app_padded_index_layout(&out));a=saved_a;
        a.view_offs+=2;require(!qwen_app_padded_index_layout(&out));a=saved_a;
        a.nb[2]-=16384;require(!qwen_app_padded_index_layout(&out));a=saved_a;
        a.ne[2]=54;require(!qwen_app_padded_index_layout(&out));a=saved_a;
        a.buffer=nullptr;require(!qwen_app_padded_index_layout(&out));a=saved_a;
        root.nb[2]-=16384;require(!qwen_app_padded_index_layout(&out));root=saved_root;
        root.nb[3]-=16384;require(!qwen_app_padded_index_layout(&out));root=saved_root;
        root.view_src=&a;require(!qwen_app_padded_index_layout(&out));root=saved_root;
        b.type=GGML_TYPE_F16;require(!qwen_app_padded_index_layout(&out));b=saved_b;
        configure_padded_index_layout(false);require(!qwen_app_padded_index_layout(&out));
    }
    for(const auto alignment:{0u,3u,32768u}){
        bool refused=false;try{configure_padded_index_layout(true,alignment);}catch(const std::invalid_argument&){refused=true;}
        require(refused);
    }
    std::uint64_t aligned=0;std::size_t request=0;
    require(padded_source_envelope(32,512u<<20,aligned,request)&&aligned==0&&request==padded_bank_stride);
    require(!padded_source_envelope((512u<<20)-bank_expert_bytes+32,512u<<20,aligned,request));
    require(!padded_source_envelope(UINT64_MAX,512u<<20,aligned,request));
    bool refused=false;try{padded_bank_slot(53,32,padded_bank_tensor_bytes,4);}catch(const std::invalid_argument&){refused=true;}
    require(refused);
}
