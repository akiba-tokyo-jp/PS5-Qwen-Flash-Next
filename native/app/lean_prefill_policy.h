// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <stdexcept>

namespace qwen_app {
struct LeanPrefillPolicy { unsigned width; bool last_output_only; };
inline LeanPrefillPolicy lean_prefill_policy(unsigned mode) {
    if(mode>5)throw std::invalid_argument("Unknown finite prefill policy");
    return {4u<<(mode/2),bool(mode&1)};
}
inline bool lean_prefill_output(LeanPrefillPolicy policy,bool prefill,unsigned row,unsigned count) {
    if(!count||count>policy.width||row>=count)
        throw std::invalid_argument("Prefill output selection exceeds its batch");
    // At least one output remains, preserving the original final-layer cache path.
    return !prefill||!policy.last_output_only||row+1==count;
}
struct LeanPrefillStats {
    std::uint64_t calls=0,input_tokens=0,output_rows=0,maximum_width=0;
};
}
extern "C" void qwen_app_lean_prefill_configure(unsigned mode);
extern "C" qwen_app::LeanPrefillStats qwen_app_lean_prefill_stats();
