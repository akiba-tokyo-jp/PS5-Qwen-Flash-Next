// SPDX-License-Identifier: MIT
// The generated data provider owns only this new shader. The selected GPU
// object redirects two resource references; its instructions stay unchanged.
#include "fused_shader_lease.h"
#include "fused_argsort_assets.h"
#include <cstring>
extern "C" {
#include "hash/sha256/sha256.h"
extern const unsigned char argsort_f32_data[];
extern const unsigned long long argsort_f32_len;
const void*__real_qwen_app_prepare_shader_code(const void*,std::size_t,std::size_t*,void**);
void qwen_app_complete_shader_code(void*);
}
namespace {
bool digest(const void*data,std::size_t bytes,const unsigned char*expected){
    sha256_t state;unsigned char result[32];sha256_init(&state);
    sha256_update(&state,static_cast<const unsigned char*>(data),bytes);sha256_final(&state,result);
    return !std::memcmp(result,expected,sizeof(result));
}
}
extern "C" const void*__wrap_qwen_app_prepare_shader_code(const void*storage,std::size_t bytes,std::size_t*decoded,void**lease){
    return qwen_app::prepare_fused_shader(storage,bytes,decoded,lease,
        {argsort_f32_data,std::size_t(argsort_f32_len),fused_argsort_original_decoded_bytes,
         qwen_fused_argsort_f32_data,std::size_t(qwen_fused_argsort_f32_len),fused_argsort_SHA256},
        {__real_qwen_app_prepare_shader_code,qwen_app_complete_shader_code,digest});
}
