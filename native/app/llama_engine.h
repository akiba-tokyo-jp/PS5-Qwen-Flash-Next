// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include "llama.h"
#include "profile_clock.h"

#include <vector>

namespace qwen_app {
struct LlamaTimingStats {
    std::uint64_t process_calls = 0, process_ns = 0, synchronize_ns = 0;
    std::uint64_t checkpoint_ns = 0, work_guard_ns = 0, stage_observer_ns = 0;
};

// Model/context admission belongs to the native launcher. This adapter borrows
// admitted objects and never initializes a driver, loads a file or deploys code.
class LlamaEngine final : public Engine {
public:
    LlamaEngine(llama_model * model, llama_context * context, std::uint32_t prefill_tokens = 1);
    ~LlamaEngine() override;
    LlamaEngine(const LlamaEngine &) = delete;
    LlamaEngine & operator=(const LlamaEngine &) = delete;
    std::uint32_t tokenize(const std::string & prompt) override;
    void prefill(std::uint32_t context_tokens) override;
    Token next() override;
    void finish() override;
    std::optional<ExpertCacheMetrics> expert_cache_metrics() const override;
    bool failed() const { return failed_; }
    LlamaTimingStats timing_stats() const { return timing_; }
    std::uint32_t prefill_batch_tokens() const { return prefill_tokens_; }
    void set_stage_observer(void (*observer)(const char *)) { stage_ = observer; }
    void set_gpu_boundaries(void (*begin)(),void (*complete)(),void (*retain)(),void (*checkpoint)()=nullptr);
    // Called before work and after synchronized decode/checkpoint boundaries.
    void set_work_guard(std::function<void()> guard, std::uint32_t prompt_token_limit = 0) {
        work_guard_ = std::move(guard); prompt_token_limit_ = prompt_token_limit;
    }

private:
    void process(llama_token token, llama_pos position, bool output);
    void process_batch(const llama_token * tokens, std::uint32_t count, llama_pos position);
    void require_healthy() const;
    llama_model * model_;
    llama_context * context_;
    const llama_vocab * vocabulary_;
    llama_batch_ext * batch_ = nullptr;
    llama_sampler * sampler_ = nullptr;
    std::vector<llama_token> prompt_;
    llama_pos position_ = 0;
    llama_token pending_ = LLAMA_TOKEN_NULL;
    std::uint32_t prefill_tokens_ = 1;
    bool ready_ = false;
    bool failed_ = false;
    void (*stage_)(const char *) = nullptr;
    void (*gpu_begin_)() = nullptr;
    void (*gpu_complete_)() = nullptr;
    void (*gpu_retain_)() = nullptr;
    void (*gpu_checkpoint_)() = nullptr;
    std::function<void()> work_guard_;
    std::uint32_t prompt_token_limit_ = 0;
    mutable LlamaTimingStats timing_;
    void guard() const {
        if (work_guard_) { ProfileScope timing(timing_.work_guard_ns); work_guard_(); }
    }
    void stage(const char * value) const {
        if (stage_) { ProfileScope timing(timing_.stage_observer_ns); stage_(value); }
    }
};

// Original BF16 remains in its container. Required PLE uses the upstream lazy
// lookup, routed experts stay in mapped CPU buffers, and the context uses a
// bounded device expert cache. Physical residency still requires qualification.
llama_model_params streaming_model_params(ggml_backend_buffer_type_t cpu_buffer);
llama_context_params streaming_context_params(std::uint32_t context_tokens,
                                              std::size_t expert_cache_bytes,
                                              std::uint32_t prefill_tokens = 1);

} // namespace qwen_app
