// SPDX-License-Identifier: MIT
#pragma once
#include <stdexcept>

namespace qwen_app {
struct SixCandidatePolicy { unsigned prefill_experts; bool late_output,graph_reuse; };
inline SixCandidatePolicy six_candidate_policy(unsigned mode) {
    if(mode!=0&&mode!=4)throw std::invalid_argument("Unknown selected normal performance policy");
    return {mode==4?6u:10u,false,mode==4};
}
}
extern "C" void qwen_app_six_configure(unsigned);
extern "C" unsigned qwen_app_six_prefill_experts();
extern "C" bool qwen_app_six_late_output();
extern "C" bool qwen_app_six_can_reuse(const void*);
extern "C" void qwen_app_six_note_inputs(const void*);
extern "C" void qwen_app_six_reused();
extern "C" unsigned long long qwen_app_six_reuse_count();
