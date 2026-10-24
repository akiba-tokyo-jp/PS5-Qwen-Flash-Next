// SPDX-License-Identifier: MIT
// Metadata only: actual GGML row cropping and actual cache eligibility method.
#include "ggml.h"
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
#define LLAMA_LOG_INFO(...) do {} while (0)
#include "actual_cache_eligibility.h"
static void check(bool ok) { if (!ok) throw std::runtime_error("Output-row/cache metadata invariant failed"); }
int main() {
    auto ctx=ggml_init({64*ggml_tensor_overhead(),nullptr,true});check(ctx);
    auto activation=ggml_new_tensor_2d(ctx,GGML_TYPE_F32,2560,1);
    auto slot_map=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,1,512);
    ActualCacheEligibility cache;cache.layers.push_back({0,slot_map,false});cache.groups.push_back({53});
    for(int outputs: {0,1}) {
        auto ids=ggml_new_tensor_1d(ctx,GGML_TYPE_I32,outputs);
        auto cropped=ggml_get_rows(ctx,activation,ids);
        check(cropped->ne[1]==outputs);
        auto selected=ggml_new_tensor_2d(ctx,GGML_TYPE_I32,10,cropped->ne[1]);
        auto admitted=cache.get_slot_map(0,selected->ne[1],selected->ne[0]);
        check(outputs ? admitted==slot_map : admitted==nullptr);
    }
    ggml_free(ctx);
    std::cout<<"{\"actual_zero_output_crop_bypasses_cache\":true,\"one_output_preserves_cache\":true,\"GPU_calls\":0,\"model_payload_reads\":0}"<<std::endl;
}
