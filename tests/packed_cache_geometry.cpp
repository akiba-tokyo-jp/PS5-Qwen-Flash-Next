// SPDX-License-Identifier: MIT
// Graph metadata only: no weights, tensor allocation, kernel or model evaluation.
#include "padded_bank.h"
#include "padded_bank_layout.h"
#include "ggml.h"
#include <iostream>
#include <stdexcept>
namespace {void check(bool v){if(!v)throw std::runtime_error("Packed cache metadata bound differs");}}
int main() {
    const auto stride=qwen_app::padded_bank_stride,plane=qwen_app::bank_expert_bytes;
    const auto bank_bytes=54*stride;check(3*bank_bytes<=(512u<<20));check(3*55*stride>(512u<<20));
    auto *ctx=ggml_init({2u<<20,nullptr,true});check(ctx!=nullptr);unsigned views=0,envelopes=0,legacy_refusals=0;
    for(bool down:{false,true}) {
        const int columns=down?640:2560,rows=down?2560:640;
        auto *old=ggml_new_tensor_3d(ctx,GGML_TYPE_BF16,columns,rows,54);
        old->nb[2]=stride;old->nb[3]=54*stride;
        auto *bytes=ggml_new_tensor_1d(ctx,GGML_TYPE_BF16,bank_bytes/2);
        for(auto residue:qwen_app::original_bank_residues) {
            auto *control=ggml_view_3d(ctx,old,columns,rows,53,columns*2,stride,residue);
            check(control->type==GGML_TYPE_BF16&&control->view_offs==residue&&control->ne[2]==53);
            auto *candidate=ggml_view_3d(ctx,bytes,columns,rows,54,columns*2,stride,residue);
            check(candidate->type==GGML_TYPE_BF16&&candidate->view_offs==residue&&candidate->ne[2]==54&&candidate->nb[2]==stride);
            check(ggml_nbytes(candidate)+residue<=bank_bytes);
            // The current 3D root cannot expose the complete last view at a nonzero residue.
            check(ggml_nbytes(candidate)+residue>ggml_nbytes(old));++legacy_refusals;
            for(unsigned slot=0;slot<54;++slot) {
                const auto start=slot*stride,request=(residue+plane+16383)&~std::size_t(16383);
                check(start<=bank_bytes&&request<=bank_bytes-start&&request<=stride);
                check(start+residue+plane<=bank_bytes);++envelopes;
            }
            ++views;
        }
    }
    ggml_free(ctx);
    std::cout<<"{\"original_residue_role_views\":"<<views<<",\"bounded_read_envelopes\":"<<envelopes
        <<",\"legacy_3D_root_54_slot_refusals\":"<<legacy_refusals<<",\"same_three_bank_bytes\":"<<3*bank_bytes
        <<",\"hypothetical_slots\":54,\"requires_new_owned_bank_and_dispatch_qualification\":true,\"model_arithmetic\":false,\"PS5_operations\":0}"<<std::endl;
}
