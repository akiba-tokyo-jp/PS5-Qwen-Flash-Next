// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
extern "C" void qwen_next_select(unsigned);
extern "C" unsigned qwen_next_experts();
extern "C" void qwen_next_routing_stats(std::uint64_t*);
extern "C" bool qwen_next_refill_before_consume();
extern "C" unsigned qwen_next_variant();
