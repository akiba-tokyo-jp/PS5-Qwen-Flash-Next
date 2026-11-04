// SPDX-License-Identifier: MIT
#include "ggml.h"

extern "C" ggml_tensor *__real_ggml_mul_mat_id(
    ggml_context *, ggml_tensor *, ggml_tensor *, ggml_tensor *);

extern "C" ggml_tensor *__wrap_ggml_mul_mat_id(
    ggml_context *ctx, ggml_tensor *weights, ggml_tensor *input, ggml_tensor *ids) {
    auto *output = __real_ggml_mul_mat_id(ctx, weights, input, ids);
    // The qualified Up path keeps FP16 storage and selects FP32 accumulation.
    if (weights->type == GGML_TYPE_IQ2_XXS) {
        output->op_params[0] = int32_t(GGML_PREC_F32);
    }
    return output;
}
