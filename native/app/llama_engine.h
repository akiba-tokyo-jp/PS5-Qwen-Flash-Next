// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include "llama.h"

#include <vector>

namespace qwen_app {

// Model/context admission belongs to the native launcher. This adapter borrows
// admitted objects and never initializes a driver, loads a file or deploys code.
class LlamaEngine final : public Engine {
public:
    LlamaEngine(llama_model * model, llama_context * context);
    ~LlamaEngine() override;
    LlamaEngine(const LlamaEngine &) = delete;
    LlamaEngine & operator=(const LlamaEngine &) = delete;
    std::uint32_t tokenize(const std::string & prompt) override;
    void prefill(std::uint32_t context_tokens) override;
    Token next() override;
    void finish() override;
    std::optional<ExpertCacheMetrics> expert_cache_metrics() const override;
    bool failed() const { return failed_; }
    void set_stage_observer(void (*observer)(const char *)) { stage_ = observer; }

private:
    void process(llama_token token, llama_pos position, bool output);
    void require_healthy() const;
    llama_model * model_;
    llama_context * context_;
    const llama_vocab * vocabulary_;
    llama_batch_ext * batch_ = nullptr;
    llama_sampler * sampler_ = nullptr;
    std::vector<llama_token> prompt_;
    llama_pos position_ = 0;
    llama_token pending_ = LLAMA_TOKEN_NULL;
    bool ready_ = false;
    bool failed_ = false;
    void (*stage_)(const char *) = nullptr;
    void stage(const char * value) const { if (stage_) stage_(value); }
};

// Original BF16 remains in its container. Required PLE uses the upstream lazy
// lookup, routed experts stay in mapped CPU buffers, and the context uses a
// bounded device expert cache. Physical residency still requires qualification.
llama_model_params streaming_model_params(ggml_backend_buffer_type_t cpu_buffer);
llama_context_params streaming_context_params(std::uint32_t context_tokens,
                                              std::size_t expert_cache_bytes);

} // namespace qwen_app
