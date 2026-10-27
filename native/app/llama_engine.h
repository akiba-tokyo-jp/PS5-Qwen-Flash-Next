// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include "llama.h"
#include "profile_clock.h"

#include <vector>
#include <array>
#include <memory>
#include <thread>

namespace qwen_app {
class ModelCheckpoint;
struct CheckpointValidationStats {
    bool enabled=false,completed=false;
    std::uint32_t captures=0,restores=0,prefill_replays=0,next_replays=0,route_rows_compared=0;
    std::uint64_t maximum_payload_bytes=0,maximum_metadata_bytes=0;
    double maximum_absolute_logit_error=0;
    std::array<std::int32_t,34> capture_positions{};
};
struct PrefixReuseStats {
    bool enabled=false,request_hit=false;
    std::uint32_t captures=0,restores=0,last_reused_prompt_tokens=0;
    std::uint64_t capture_ns=0,restore_ns=0;
};
struct SpeculativeStepStats {
    bool enabled=false,controller_enabled=false;
    std::uint32_t attempts=0,accepted=0,rejected=0,queued_bonus_samples=0;
    std::uint32_t proposal_checks=0,no_draft=0,prompt_proposals=0,generated_proposals=0;
};
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
    void enable_checkpoint_validation(std::function<void(std::uint64_t)> admit,
        std::function<std::uint32_t()> route_cursor,
        std::function<void(std::uint32_t,std::uint32_t,std::uint32_t)> compare_routes);
    CheckpointValidationStats checkpoint_validation_stats()const{return checkpoint_stats_;}
    void enable_prefix_reuse(std::function<void(std::uint64_t)> admit);
    PrefixReuseStats prefix_reuse_stats()const{return prefix_stats_;}
    void set_logits_observer(std::function<void(const float *,std::size_t)> observer);
    // Default-off experimental APIs. Native width-two arithmetic and speed
    // require their own finite qualification; host checks do not establish them.
    void enable_speculative_step_prototype(std::function<void(std::uint64_t)> admit);
    void enable_model_free_speculation(std::function<void(std::uint64_t)> admit);
    Token next_with_one_draft(llama_token draft);
    SpeculativeStepStats speculative_step_stats()const{return speculative_stats_;}
    // Called before work and after synchronized decode/checkpoint boundaries.
    void set_work_guard(std::function<void()> guard, std::uint32_t prompt_token_limit = 0) {
        work_guard_ = std::move(guard); prompt_token_limit_ = prompt_token_limit;
    }

private:
    void process(llama_token token, llama_pos position, bool output);
    void process_batch(const llama_token * tokens, std::uint32_t count, llama_pos position);
    void process_batch_once(const llama_token * tokens, std::uint32_t count, llama_pos position);
    Token next_once();
    Token validate_next_checkpoint();
    const float *effective_logits()const;
    void capture_checkpoint_in_active_epoch();
    void restore_checkpoint_in_active_epoch();
    void compare_checkpoint_logits();
    void compare_checkpoint_routes(std::uint32_t first,std::uint32_t first_end,std::uint32_t second);
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
    std::unique_ptr<ModelCheckpoint> checkpoint_;
    CheckpointValidationStats checkpoint_stats_;
    PrefixReuseStats prefix_stats_;
    SpeculativeStepStats speculative_stats_;
    bool speculative_bonus_ready_=false;
    std::vector<float> speculative_bonus_logits_;
    std::vector<llama_token> speculative_committed_tokens_;
    std::function<void(const float *,std::size_t)> logits_observer_;
    std::function<void(std::uint64_t)> checkpoint_admit_;
    std::function<std::uint32_t()> checkpoint_route_cursor_;
    std::function<void(std::uint32_t,std::uint32_t,std::uint32_t)> checkpoint_compare_routes_;
    std::vector<float> checkpoint_reference_logits_,restored_logits_;
    std::vector<llama_token_data> checkpoint_candidates_;
    std::uint64_t request_epoch_=0;
    std::thread::id producer_=std::this_thread::get_id();
    bool inside_prefill_=false,restored_logits_active_=false;
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
