// SPDX-License-Identifier: MIT
#include "llama_engine.h"
#include "expert_policy.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace qwen_app {
namespace {
void require_prefill_width(std::uint32_t tokens) {
    if (tokens != 1 && tokens != 2 && tokens != 4)
        throw std::invalid_argument("Bounded prefill requires 1, 2 or 4 tokens");
}
class GpuBoundary {
    void (*complete_)();
    void (*retain_)();
    bool completed_=false;
public:
    GpuBoundary(void (*begin)(),void (*complete)(),void (*retain)()) : complete_(complete),retain_(retain) {
        if(begin)begin();
    }
    void complete() {if(complete_)complete_();completed_=true;}
    ~GpuBoundary() {if(!completed_ && retain_)retain_();}
};
}

void LlamaEngine::set_gpu_boundaries(void (*begin)(),void (*complete)(),void (*retain)(),void (*checkpoint)()) {
    if(!begin || !complete || !retain || ready_)throw std::invalid_argument("Complete GPU boundary hooks are required before requests");
    gpu_begin_=begin;gpu_complete_=complete;gpu_retain_=retain;
    gpu_checkpoint_=checkpoint;
}

std::optional<ExpertCacheMetrics> LlamaEngine::expert_cache_metrics() const {
    llama_app_expert_stats stats{};
    llama_app_expert_counters(&stats);
    return ExpertCacheMetrics{stats.hits, stats.misses, stats.uploaded_bytes, stats.prefetch_advice_bytes};
}

llama_model_params streaming_model_params(ggml_backend_buffer_type_t cpu_buffer) {
    if (!cpu_buffer) throw std::invalid_argument("A mapped CPU buffer type is required");
    // Initialization and model loading are serialized by the application owner.
    static llama_model_tensor_buft_override overrides[2];
    overrides[0] = {"\\.ffn_(gate|up|down|gate_up)_exps\\.weight$", cpu_buffer};
    overrides[1] = {nullptr, nullptr};
    auto params = llama_model_default_params();
    params.n_gpu_layers = -1;
    params.split_mode = LLAMA_SPLIT_MODE_NONE;
    params.load_mode = LLAMA_LOAD_MODE_MMAP;
    params.lazy_mode = LLAMA_LAZY_MODE_ON;
    params.tensor_buft_overrides = overrides;
    params.load_mtp = false;
    params.use_extra_bufts = false;
    // The complete native SHA/metadata gate precedes loading. Generic tensor
    // scanning would dereference reserved source keys rather than bounded I/O.
    params.check_tensors = false;
    return params;
}

llama_context_params streaming_context_params(std::uint32_t context_tokens,
                                              std::size_t expert_cache_bytes,
                                              std::uint32_t prefill_tokens) {
    require_prefill_width(prefill_tokens);
    if (context_tokens < 2 || !expert_cache_bytes) throw std::invalid_argument("Invalid streaming budget");
    if (prefill_tokens > context_tokens ||
        (prefill_tokens > 1 && expert_cache_bytes != (512u << 20)))
        throw std::invalid_argument("Batched prefill requires the complete admitted 512 MiB expert cache");
    auto params = llama_context_default_params();
    params.n_ctx = context_tokens;
    params.n_batch = params.n_ubatch = prefill_tokens;
    params.n_seq_max = 1;
    params.n_threads = params.n_threads_batch = 6;
    params.offload_kqv = true;
    params.op_offload = true;
    params.moe_cache_size = expert_cache_bytes;
    params.no_perf = false;
    params.type_k = params.type_v = GGML_TYPE_F32;
    return params;
}

LlamaEngine::LlamaEngine(llama_model * model, llama_context * context, std::uint32_t prefill_tokens)
    : model_(model), context_(context), vocabulary_(model ? llama_model_get_vocab(model) : nullptr),
      prefill_tokens_(prefill_tokens) {
    require_prefill_width(prefill_tokens_);
    if (!model_ || !context_ || !vocabulary_) throw std::invalid_argument("Admitted model and context required");
    if (llama_n_batch(context_) < prefill_tokens_ || llama_n_ubatch(context_) < prefill_tokens_)
        throw std::invalid_argument("Context capacity is smaller than the explicit prefill width");
    batch_ = llama_batch_ext_init(context_);
    if (!batch_) throw std::runtime_error("Batch allocation failed");
    sampler_ = llama_sampler_init_greedy();
    if (!sampler_) {
        llama_batch_ext_free(batch_);
        throw std::runtime_error("Sampler allocation failed");
    }
}

LlamaEngine::~LlamaEngine() {
    if (failed_) return; // Retain uncertain resources until the owning process closes normally.
    llama_sampler_free(sampler_);
    llama_batch_ext_free(batch_);
}

void LlamaEngine::require_healthy() const {
    if (failed_) throw std::runtime_error("Model adapter is quarantined");
}

std::uint32_t LlamaEngine::tokenize(const std::string & prompt) {
    require_healthy();
    stage("inference_before_tokenization");
    if (ready_ || prompt.size() > std::size_t(std::numeric_limits<std::int32_t>::max()))
        throw std::invalid_argument("Invalid prompt state or length");
    const int length = static_cast<int>(prompt.size());
    const int result = llama_tokenize(vocabulary_, prompt.data(), length, nullptr, 0, true, true);
    if (result >= 0 || result == std::numeric_limits<int>::min()) throw std::runtime_error("Token sizing failed");
    if (prompt_token_limit_ && std::uint32_t(-result) > prompt_token_limit_)
        throw std::invalid_argument("Rendered prompt exceeds its admitted token bound");
    prompt_.resize(std::size_t(-result));
    const int count = llama_tokenize(vocabulary_, prompt.data(), length, prompt_.data(), int(prompt_.size()), true, true);
    if (count <= 0 || std::size_t(count) > prompt_.size()) throw std::runtime_error("Tokenization failed");
    prompt_.resize(std::size_t(count));
    stage("inference_tokenization_completed");
    return std::uint32_t(count);
}

void LlamaEngine::process(llama_token token, llama_pos position, bool output) {
    if (!output) throw std::invalid_argument("Bounded source execution requires output/cache eligibility");
    process_batch(&token, 1, position);
}

void LlamaEngine::process_batch(const llama_token * tokens, std::uint32_t count, llama_pos position) {
    if (!tokens || !count || count > prefill_tokens_ || position < 0 ||
        std::uint64_t(position) + count > llama_n_ctx(context_))
        throw std::invalid_argument("Invalid bounded causal batch");
    guard();
    llama_batch_ext_clear(batch_);
    for (std::uint32_t i = 0; i < count; ++i) {
        const auto index = llama_batch_ext_add_token(batch_, 0, tokens[i]);
        const llama_pos causal_position = position + i;
        if (index < 0 || !llama_batch_ext_set_pos(batch_, index, &causal_position) ||
            !llama_batch_ext_set_output_logits(batch_, index, true))
            throw std::runtime_error("Batch setup failed");
    }
    stage("inference_before_decode_call");
    {
        ProfileScope timing(timing_.process_ns);
        if (llama_process(context_, LLAMA_PROCESS_TYPE_DECODE, batch_) != 0)
            throw std::runtime_error("Model decode failed");
        ++timing_.process_calls;
    }
    stage("inference_decode_call_returned_before_synchronize");
    { ProfileScope timing(timing_.synchronize_ns); llama_synchronize(context_); }
    stage("inference_decode_synchronization_completed");
    if(gpu_checkpoint_) { ProfileScope timing(timing_.checkpoint_ns); gpu_checkpoint_(); }
    guard();
}

void LlamaEngine::prefill(std::uint32_t context_tokens) {
    require_healthy();
    if (prompt_.empty() || prompt_.size() >= context_tokens || context_tokens > llama_n_ctx(context_))
        throw std::invalid_argument("Invalid context admission");
    try {
        guard();
        GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);
        stage("inference_before_prefill");
        llama_memory_clear(llama_get_memory(context_), true);
        llama_sampler_reset(sampler_);
        position_ = 0;
        pending_ = LLAMA_TOKEN_NULL;
        for (std::size_t i = 0; i < prompt_.size();) {
            // A zero-output single-token batch crops the final Qwen layer to
            // zero rows, which disables its expert-slot cache path. Request
            // every prompt output; sampling still uses only the final logits.
            const auto count = std::uint32_t(std::min<std::size_t>(prefill_tokens_, prompt_.size() - i));
            process_batch(prompt_.data() + i, count, position_);
            position_ += count;
            i += count;
        }
        boundary.complete();ready_ = true;
        stage("inference_prefill_completed");
    } catch (...) { failed_ = true; throw; }
}

Token LlamaEngine::next() {
    require_healthy();
    if (!ready_) throw std::logic_error("Prefill required before decoding");
    try {
        guard();
        GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);
        if (pending_ != LLAMA_TOKEN_NULL) {
            if (std::uint32_t(position_) >= llama_n_ctx(context_)) throw std::runtime_error("Context exhausted");
            process(pending_, position_++, true);
        }
        const auto count = llama_vocab_n_tokens(vocabulary_);
        const auto * logits = llama_get_logits_ith(context_, -1);
        if (!logits || count <= 0) throw std::runtime_error("Missing logits");
        for (int i = 0; i < count; ++i) {
            if (!std::isfinite(logits[i])) throw std::runtime_error("Non-finite model logits");
        }
        stage("inference_before_sampling");
        pending_ = llama_sampler_sample(sampler_, context_, -1);
        if (pending_ < 0 || pending_ >= count) throw std::runtime_error("Invalid sampled token");
        if (llama_vocab_is_eog(vocabulary_, pending_)) { boundary.complete();stage("inference_end_of_generation_observed"); return {pending_, {}, true}; }
        std::string piece(256, '\0');
        int size = llama_token_to_piece(vocabulary_, pending_, piece.data(), int(piece.size()), 0, true);
        if (size < 0) {
            if (size < -(1 << 20)) throw std::runtime_error("Token piece exceeds output bound");
            piece.resize(std::size_t(-size));
            size = llama_token_to_piece(vocabulary_, pending_, piece.data(), int(piece.size()), 0, true);
        }
        if (size < 0 || std::size_t(size) > piece.size()) throw std::runtime_error("Token rendering failed");
        piece.resize(std::size_t(size));
        boundary.complete();stage("inference_token_ready");
        return {pending_, std::move(piece), false};
    } catch (...) { failed_ = true; throw; }
}

void LlamaEngine::finish() {
    require_healthy();
    try {
    guard();
    GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);
    stage("inference_before_successful_request_reset");
    llama_memory_clear(llama_get_memory(context_), true);
    llama_sampler_reset(sampler_);
    ready_ = false;
    pending_ = LLAMA_TOKEN_NULL;
    prompt_.clear();
    boundary.complete();stage("inference_request_reset_completed");
    } catch (...) {failed_=true;throw;}
}

} // namespace qwen_app
