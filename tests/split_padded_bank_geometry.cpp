// SPDX-License-Identifier: MIT
#include "split_padded_bank.h"
#include "padded_bank_layout.h"
#include "ggml.h"
#include <iostream>
#include <stdexcept>
namespace {void check(bool ok){if(!ok)throw std::runtime_error("Split bank metadata differs");}}
int main() {
    auto *ctx=ggml_init({2u<<20,nullptr,true});check(ctx!=nullptr);unsigned views=0,envelopes=0;
    for(bool down:{false,true})for(unsigned group=0;group<2;++group) {
        const int columns=down?640:2560,rows=down?2560:640;
        const auto bytes=qwen_app::split_bank_planes[group]*qwen_app::padded_bank_stride;
        auto *root=ggml_new_tensor_1d(ctx,GGML_TYPE_BF16,bytes/2);
        for(auto residue:qwen_app::original_bank_residues) {
            auto *view=ggml_view_3d(ctx,root,columns,rows,qwen_app::split_bank_active[group],columns*2,qwen_app::padded_bank_stride,residue);
            check(ggml_nbytes(view)+residue<=bytes&&view->ne[2]==std::int64_t(qwen_app::split_bank_active[group]));++views;
            for(unsigned local=0;local<qwen_app::split_bank_active[group];++local) {
                const auto global=local+(group?26:0);const auto slot=qwen_app::split_padded_slot(global,residue,32);
                check(slot.group==group&&slot.local_slot==local&&slot.role_allocation_bytes==bytes);
                check(slot.envelope.payload_offset+qwen_app::bank_expert_bytes<=bytes&&slot.envelope.aligned_write_offset%16384==0);
                ++envelopes;
            }
        }
    }
    ggml_free(ctx);unsigned refused=0;
    const auto bad=[&](std::size_t slot,std::size_t residue,std::size_t alignment){try{qwen_app::split_padded_slot(slot,residue,alignment);}catch(...){++refused;return;}throw std::runtime_error("Invalid split slot accepted");};
    bad(53,32,32);bad(52,16384,32);bad(52,33,32);bad(0,0,0);bad(0,0,3);
    check(views==120&&envelopes==3180&&refused==5&&qwen_app::split_bank_total_bytes==533495808);
    std::cout<<"{\"actual_GGML_role_residue_views\":"<<views<<",\"bounded_read_envelopes\":"<<envelopes
        <<",\"refusals\":"<<refused<<",\"global_active_slots\":53,\"total_physical_planes_per_role\":54,\"same_three_role_bytes\":"
        <<qwen_app::split_bank_total_bytes<<",\"native_owned_dispatch_qualification\":false,\"model_arithmetic\":false,\"PS5_operations\":0}"<<std::endl;
}
