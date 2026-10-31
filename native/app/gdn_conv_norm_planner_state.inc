// SPDX-License-Identifier: MIT
// Metadata-only planner diagnostics; no addresses, activations or weights.
static std::array<std::atomic<std::uint64_t>,8>qwen_conv_norm_planner_counts{};
extern "C" void qwen_app_conv_norm_planner_stats(std::uint64_t*out){
    for(unsigned i=0;i<qwen_conv_norm_planner_counts.size();++i)out[i]=qwen_conv_norm_planner_counts[i].load(std::memory_order_relaxed);
}
