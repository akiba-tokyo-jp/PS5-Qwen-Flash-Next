// SPDX-License-Identifier: MIT
#pragma once
#include <cstddef>
struct ggml_tensor;
namespace qwen_app {void configure_native_padded_cache(bool,std::size_t);}
extern "C" {
bool qwen_app_padded_cache_enabled();
std::size_t qwen_app_padded_source_residue(const void *,std::size_t);
bool qwen_app_try_owned_bank_reads(ggml_tensor *,const void *,const void *,unsigned,
    const int *,std::size_t);
bool qwen_app_read_owned_bank(const void *,const void *,unsigned,const int *,
    std::size_t,void *,std::size_t,std::size_t);
void qwen_app_record_padded_scatter(std::size_t);
}
