// SPDX-License-Identifier: MIT
#include "prefill16_policy.h"
static_assert(qwen_app::supported_sharing_prefill_width(4));
static_assert(qwen_app::supported_sharing_prefill_width(16));
static_assert(!qwen_app::supported_sharing_prefill_width(0));
static_assert(!qwen_app::supported_sharing_prefill_width(1));
static_assert(!qwen_app::supported_sharing_prefill_width(2));
static_assert(!qwen_app::supported_sharing_prefill_width(8));
static_assert(!qwen_app::supported_sharing_prefill_width(17));
int main(){}
