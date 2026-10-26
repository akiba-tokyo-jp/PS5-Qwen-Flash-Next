// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include <stdexcept>
namespace qwen_app {
// Observation only: borrow the original resident router. No expert loads or
// routing decisions are changed. A native caller still has to qualify actual
// placement, bounded observer storage, graph retirement and readback overhead.
inline ggml_tensor *build_router_shadow(ggml_context *ctx,ggml_tensor *early,ggml_tensor *router) {
    if(!ctx||!early||!router||early->type!=GGML_TYPE_F32||early->ne[0]!=2560||early->ne[1]<1||early->ne[1]>4||
       early->ne[2]!=1||early->ne[3]!=1||!ggml_is_contiguous(early)||router->type!=GGML_TYPE_F32||
       router->ne[0]!=2560||router->ne[1]!=512||router->ne[2]!=1||router->ne[3]!=1||!ggml_is_contiguous(router))
        throw std::invalid_argument("Router shadow requires the original F32 router and bounded actual early hidden input");
    auto *logits=ggml_mul_mat(ctx,router,early);
    auto *probabilities=ggml_soft_max(ctx,logits);
    auto *ids=ggml_argsort_top_k(ctx,probabilities,10);
    ggml_set_output(ids);return ids;
}
}
