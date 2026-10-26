// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
enum class PLESliceMode:unsigned {control=0,coefficient_copy_elided=1,shift_copy_elided=2,both_copies_elided=3};
struct PLETaps {ggml_tensor *shifted=nullptr,*coefficient=nullptr;};
// Unqualified graph prototype, never selected by the production graph. Widths
// and original PLE history/layout are deliberately restricted. A strided MUL
// requires positive Vulkan placement qualification: the current CPU MUL does
// not support this src0 stride. No backend predicate is relaxed here.
inline PLETaps build_experimental_PLE_tap(ggml_context *ctx,ggml_tensor *padded,ggml_tensor *kernel,
        unsigned tokens,unsigned tap,PLESliceMode mode) {
    const auto flags=static_cast<unsigned>(mode);
    if(!ctx||!padded||!kernel||flags>3||!tokens||tokens>4||tap>=4||
       padded->type!=GGML_TYPE_F32||padded->ne[0]!=9+tokens||padded->ne[1]!=10240||padded->ne[2]!=1||padded->ne[3]!=1||
       !ggml_is_contiguous(padded)||kernel->type!=GGML_TYPE_BF16||kernel->ne[0]!=4||kernel->ne[1]!=10240||
       kernel->ne[2]!=1||kernel->ne[3]!=1||!ggml_is_contiguous(kernel))
        throw std::invalid_argument("Exact original bounded PLE history/kernel geometry required");
    auto *shifted=ggml_transpose(ctx,ggml_view_3d(ctx,padded,tokens,10240,1,padded->nb[1],padded->nb[2],tap*3*sizeof(float)));
    if(!(flags&2))shifted=ggml_cont(ctx,shifted);
    auto *coefficient=ggml_view_2d(ctx,kernel,1,10240,kernel->nb[1],tap*kernel->nb[0]);
    if(flags&1) {
        // The existing strided BF16 -> F32 copy produces the same contiguous
        // F32 column. Retain conversion; omit only its preceding BF16 gather.
        coefficient=ggml_cast(ctx,coefficient,GGML_TYPE_F32);
        coefficient=ggml_reshape_1d(ctx,coefficient,10240);
    }else {
        coefficient=ggml_reshape_1d(ctx,ggml_cont(ctx,coefficient),10240);
        coefficient=ggml_cast(ctx,coefficient,GGML_TYPE_F32);
    }
    return {shifted,coefficient};
}
}
