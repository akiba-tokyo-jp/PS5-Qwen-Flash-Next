// SPDX-License-Identifier: MIT
#include "llama_engine.h"
#include "expert_policy.h"

#include <cmath>
#include <limits>
#include <stdexcept>

namespace qwen_app {

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
    return params;
}

llama_context_params streaming_context_params(std::uint32_t context_tokens,
                                              std::size_t expert_cache_bytes) {
    if (context_tokens < 2 || !expert_cache_bytes) throw std::invalid_argument("Invalid streaming budget");
    auto params = llama_context_default_params();
    params.n_ctx = context_tokens;
    params.n_batch = params.n_ubatch = params.n_seq_max = 1;
    params.n_threads = params.n_threads_batch = 6;
    params.moe_cache_size = expert_cache_bytes;
    params.no_perf = false;
    params.type_k = params.type_v = GGML_TYPE_F32;
    return params;
}

LlamaEngine::LlamaEngine(llama_model * model, llama_context * context)
    : model_(model), context_(context), vocabulary_(model ? llama_model_get_vocab(model) : nullptr) {
    if (!model_ || !context_ || !vocabulary_) throw std::invalid_argument("Admitted model and context required");
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
    if (ready_ || prompt.size() > std::size_t(std::numeric_limits<std::int32_t>::max()))
        throw std::invalid_argument("Invalid prompt state or length");
    const int length = static_cast<int>(prompt.size());
    const int result = llama_tokenize(vocabulary_, prompt.data(), length, nullptr, 0, true, true);
    if (result >= 0 || result == std::numeric_limits<int>::min()) throw std::runtime_error("Token sizing failed");
    prompt_.resize(std::size_t(-result));
    const int count = llama_tokenize(vocabulary_, prompt.data(), length, prompt_.data(), int(prompt_.size()), true, true);
    if (count <= 0 || std::size_t(count) > prompt_.size()) throw std::runtime_error("Tokenization failed");
    prompt_.resize(std::size_t(count));
    return std::uint32_t(count);
}

void LlamaEngine::process(llama_token token, llama_pos position, bool output) {
    llama_batch_ext_clear(batch_);
    const auto index = llama_batch_ext_add_token(batch_, 0, token);
    if (index < 0 || !llama_batch_ext_set_pos(batch_, index, &position) ||
        !llama_batch_ext_set_output_logits(batch_, index, output)) throw std::runtime_error("Batch setup failed");
    if (llama_process(context_, LLAMA_PROCESS_TYPE_DECODE, batch_) != 0)
        throw std::runtime_error("Model decode failed");
    llama_synchronize(context_);
}

void LlamaEngine::prefill(std::uint32_t context_tokens) {
    require_healthy();
    if (prompt_.empty() || prompt_.size() >= context_tokens || context_tokens > llama_n_ctx(context_))
        throw std::invalid_argument("Invalid context admission");
    try {
        llama_memory_clear(llama_get_memory(context_), true);
        llama_sampler_reset(sampler_);
        position_ = 0;
        pending_ = LLAMA_TOKEN_NULL;
        for (std::size_t i = 0; i < prompt_.size(); ++i) {
            process(prompt_[i], position_++, i + 1 == prompt_.size());
        }
        ready_ = true;
    } catch (...) { failed_ = true; throw; }
}

Token LlamaEngine::next() {
    require_healthy();
    if (!ready_) throw std::logic_error("Prefill required before decoding");
    try {
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
        pending_ = llama_sampler_sample(sampler_, context_, -1);
        if (pending_ < 0 || pending_ >= count) throw std::runtime_error("Invalid sampled token");
        if (llama_vocab_is_eog(vocabulary_, pending_)) return {pending_, {}, true};
        std::string piece(256, '\0');
        int size = llama_token_to_piece(vocabulary_, pending_, piece.data(), int(piece.size()), 0, true);
        if (size < 0) {
            if (size < -(1 << 20)) throw std::runtime_error("Token piece exceeds output bound");
            piece.resize(std::size_t(-size));
            size = llama_token_to_piece(vocabulary_, pending_, piece.data(), int(piece.size()), 0, true);
        }
        if (size < 0 || std::size_t(size) > piece.size()) throw std::runtime_error("Token rendering failed");
        piece.resize(std::size_t(size));
        return {pending_, std::move(piece), false};
    } catch (...) { failed_ = true; throw; }
}

void LlamaEngine::finish() {
    require_healthy();
    llama_memory_clear(llama_get_memory(context_), true);
    llama_sampler_reset(sampler_);
    ready_ = false;
    pending_ = LLAMA_TOKEN_NULL;
    prompt_.clear();
}

} // namespace qwen_app
