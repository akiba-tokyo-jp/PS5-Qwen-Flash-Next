// SPDX-License-Identifier: MIT
#pragma once
#include "ggml-backend.h"
#include <cstdint>
#include <nlohmann/json.hpp>
struct llama_context;
namespace qwen_app {
bool evaluate_router_shadow(ggml_tensor*,bool ask,void*)noexcept;
void start_router_shadow_request(llama_context*,std::uint64_t request,bool enabled,
    ggml_backend_buffer_type_t,void(*guard)(),std::uint64_t(*clock)(),void(*checkpoint)());
void begin_router_shadow_process(unsigned width);
void complete_router_shadow_process();
nlohmann::json finish_router_shadow_request(llama_context*);
}
extern "C" bool qwen_app_router_shadow_graph_enabled();
