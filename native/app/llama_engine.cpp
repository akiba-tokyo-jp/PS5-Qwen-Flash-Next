// SPDX-License-Identifier: MIT
#include "llama_engine.h"
#include "expert_policy.h"
#include "indexed_vector.h"
#include "mapped_copy.h"
#include "model_checkpoint.h"
#include "padded_cache_geometry.h"
#include "model_free_draft.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <atomic>

namespace {
std::atomic<bool> indexed_vector_enabled{false},indexed_vector_scope{false};
std::atomic<std::uint64_t> indexed_matrix_calls{0},indexed_vector_calls{0},mapped_write_bytes{0},staging_write_bytes{0};
}
extern "C" bool qwen_app_bf16_indexed_vector_enabled() {
    return indexed_vector_enabled.load(std::memory_order_relaxed) && indexed_vector_scope.load(std::memory_order_relaxed);
}
extern "C" void qwen_app_record_bf16_indexed_path(bool vector) {
    (vector?indexed_vector_calls:indexed_matrix_calls).fetch_add(1,std::memory_order_relaxed);
}
extern "C" void qwen_app_record_upload_path(bool mapped,std::uint64_t bytes) {
    (mapped?mapped_write_bytes:staging_write_bytes).fetch_add(bytes,std::memory_order_relaxed);
}

namespace qwen_app {
void configure_bf16_indexed_vector(bool enabled) { indexed_vector_enabled.store(enabled,std::memory_order_relaxed); }
void set_bf16_indexed_vector_scope(bool active) { indexed_vector_scope.store(active,std::memory_order_relaxed); }
GpuPathStats gpu_path_stats() {
    return {indexed_matrix_calls.load(std::memory_order_relaxed),indexed_vector_calls.load(std::memory_order_relaxed),
        mapped_write_bytes.load(std::memory_order_relaxed),staging_write_bytes.load(std::memory_order_relaxed)};
}
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
        (prefill_tokens > 1 && expert_cache_bytes != selected_padded_cache_geometry().cache_bytes())||
        (selected_padded_cache_geometry().active_slots==128&&context_tokens!=256))
        throw std::invalid_argument("Batched prefill requires the complete selected cache and context scope");
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
    if(checkpoint_&&producer_!=std::this_thread::get_id())throw std::runtime_error("Checkpoint adapter requires its original producer");
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
    if(request_epoch_==UINT64_MAX)throw std::runtime_error("Request epoch exhausted");
    ++request_epoch_;
    stage("inference_tokenization_completed");
    return std::uint32_t(count);
}

void LlamaEngine::process(llama_token token, llama_pos position, bool output) {
    if (!output) throw std::invalid_argument("Bounded source execution requires output/cache eligibility");
    // Only next-token decode selects the candidate; partial prefill stays on
    // the existing matrix route. Reset selection on every exception as well.
    struct Scope {
        Scope() { set_bf16_indexed_vector_scope(true);set_mapped_copy_scope(true); }
        ~Scope() { set_mapped_copy_scope(false);set_bf16_indexed_vector_scope(false); }
    } scope;
    process_batch(&token, 1, position);
}

void LlamaEngine::process_batch(const llama_token * tokens, std::uint32_t count, llama_pos position) {
    if(checkpoint_stats_.enabled&&inside_prefill_&&(position==4||position==28)) {
        capture_checkpoint_in_active_epoch();
        const auto first=checkpoint_route_cursor_();
        process_batch_once(tokens,count,position);
        const auto first_end=checkpoint_route_cursor_();
        const auto *reference=effective_logits();const auto vocabulary=llama_vocab_n_tokens(vocabulary_);
        if(!reference||vocabulary<=0)throw std::runtime_error("Checkpoint prefill reference logits unavailable");
        checkpoint_reference_logits_.assign(reference,reference+vocabulary);
        restore_checkpoint_in_active_epoch();
        const auto second=checkpoint_route_cursor_();process_batch_once(tokens,count,position);
        compare_checkpoint_logits();compare_checkpoint_routes(first,first_end,second);
        ++checkpoint_stats_.prefill_replays;stage("model_checkpoint_prefill_replay_verified");return;
    }
    process_batch_once(tokens,count,position);
}

void LlamaEngine::process_batch_once(const llama_token * tokens, std::uint32_t count, llama_pos position) {
    if (!tokens || !count || count > prefill_tokens_ || position < 0 ||
        std::uint64_t(position) + count > llama_n_ctx(context_))
        throw std::invalid_argument("Invalid bounded causal batch");
    restored_logits_active_=false;
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
    if(expert_hooks_.before_process)expert_hooks_.before_process();
    const auto online_started=expert_hooks_.completed_ordinary?ProfileClock::now():ProfileClock::time_point{};
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
    if(expert_hooks_.completed_ordinary&&count==1)
        expert_hooks_.completed_ordinary(tokens[0],profile_elapsed_ns(online_started));
    guard();
}

void LlamaEngine::prefill(std::uint32_t context_tokens) {
    require_healthy();
    if(speculative_stats_.enabled&&(ready_||speculative_bonus_ready_))
        throw std::invalid_argument("A speculative request cannot prefill again before successful request cleanup");
    if (prompt_.empty() || prompt_.size() >= context_tokens || context_tokens > llama_n_ctx(context_))
        throw std::invalid_argument("Invalid context admission");
    try {
        guard();
        GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);
        stage("inference_before_prefill");
        if(prefix_stats_.enabled&&checkpoint_->matches_complete_prompt(prompt_)) {
            {ProfileScope timing(prefix_stats_.restore_ns);
                checkpoint_->rebind_complete_prompt(request_epoch_,prompt_);
                restore_checkpoint_in_active_epoch();}
            if(!ready_||pending_!=LLAMA_TOKEN_NULL||position_!=llama_pos(prompt_.size()))
                throw std::runtime_error("Restored prefix is not a complete unsampled prompt");
            boundary.complete();++prefix_stats_.restores;prefix_stats_.request_hit=true;
            prefix_stats_.last_reused_prompt_tokens=std::uint32_t(prompt_.size());
            stage("inference_exact_prefix_prefill_restored_completed");return;
        }
        prefix_stats_.request_hit=false;prefix_stats_.last_reused_prompt_tokens=0;
        llama_memory_clear(llama_get_memory(context_), true);
        llama_sampler_reset(sampler_);
        position_ = 0;
        pending_ = LLAMA_TOKEN_NULL;
        inside_prefill_=true;
        for (std::size_t i = 0; i < prompt_.size();) {
            // A zero-output single-token batch crops the final Qwen layer to
            // zero rows, which disables its expert-slot cache path. Request
            // every prompt output; sampling still uses only the final logits.
            const auto count = std::uint32_t(std::min<std::size_t>(prefill_tokens_, prompt_.size() - i));
            process_batch(prompt_.data() + i, count, position_);
            position_ += count;
            i += count;
        }
        inside_prefill_=false;
        if(prefix_stats_.enabled) {
            ready_=true;
            {ProfileScope timing(prefix_stats_.capture_ns);capture_checkpoint_in_active_epoch();}
            ++prefix_stats_.captures;
        }
        boundary.complete();ready_ = true;
        stage("inference_prefill_completed");
    } catch (...) { inside_prefill_=false;failed_ = true; throw; }
}

Token LlamaEngine::next() {
    const bool bonus=speculative_bonus_ready_;
    if(speculative_bonus_ready_) {
        require_healthy();
        restored_logits_=std::move(speculative_bonus_logits_);restored_logits_active_=true;
        speculative_bonus_ready_=false;pending_=LLAMA_TOKEN_NULL;++speculative_stats_.queued_bonus_samples;
    }
    if(checkpoint_stats_.enabled)return validate_next_checkpoint();
    Token result;
    if(speculative_stats_.controller_enabled) {
        require_healthy();
        if(!ready_||speculative_committed_tokens_.size()>=32)
            throw std::invalid_argument("The causal width-two controller requires its bounded active request");
        // History contains only already returned tokens. Leave room for both
        // verified outputs, and never replace a pending queued bonus/draft.
        if(!bonus&&pending_!=LLAMA_TOKEN_NULL&&!llama_vocab_is_eog(vocabulary_,pending_)&&
           !speculative_committed_tokens_.empty()&&speculative_committed_tokens_.size()<=30&&
           std::uint64_t(position_)+2<=llama_n_ctx(context_)&&speculative_stats_.attempts<32) {
            ++speculative_stats_.proposal_checks;
            const auto draft=propose_model_free_token(prompt_.data(),prompt_.size(),
                speculative_committed_tokens_.data(),speculative_committed_tokens_.size(),
                std::size_t(llama_vocab_n_tokens(vocabulary_)),DraftEvidence::consistent_pair);
            if(draft.found&&!llama_vocab_is_eog(vocabulary_,draft.token)) {
                if(draft.origin==DraftOrigin::prompt)++speculative_stats_.prompt_proposals;
                else ++speculative_stats_.generated_proposals;
                unsigned width=2;
                if(expert_hooks_.choose) {
                    ++speculative_stats_.cost_checks;width=expert_hooks_.choose(pending_,draft.token);
                    if(width!=1&&width!=2)throw std::runtime_error("The native expert-aware scope permits only width one or two");
                    if(width==1)++speculative_stats_.cost_ordinary;else ++speculative_stats_.cost_width_two;
                }
                result=width==2?next_with_one_draft(draft.token):next_once();
            } else {++speculative_stats_.no_draft;result=next_once();}
        }else result=next_once();
        if(!result.end_of_generation)speculative_committed_tokens_.push_back(result.id);
        return result;
    }
    return next_once();
}

Token LlamaEngine::next_with_one_draft(llama_token draft) {
    require_healthy();
    const auto count=llama_vocab_n_tokens(vocabulary_);
    if(!speculative_stats_.enabled||!checkpoint_||!ready_||pending_==LLAMA_TOKEN_NULL||
       llama_vocab_is_eog(vocabulary_,pending_)||speculative_bonus_ready_||draft<0||draft>=count||
       count<=0||count>262144||std::uint64_t(position_)+2>llama_n_ctx(context_)||speculative_stats_.attempts>=32)
        throw std::invalid_argument("One draft requires an original pending token and an admitted bounded prototype owner");
    try {
        guard();
        {
            GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);
            ++speculative_stats_.attempts;
            auto cost_start=ProfileClock::now();capture_checkpoint_in_active_epoch();
            const auto capture_seconds=double(profile_elapsed_ns(cost_start))/1e9;
            double restore_seconds=0;bool draft_accepted=false;
            const llama_token pair[]={pending_,draft};
            // Two original causal target tokens, not two draft tokens. The
            // existing matrix route remains selected, independently of prefill.
            process_batch_once(pair,2,position_);
            const auto *first=llama_get_logits_ith(context_,0),*second=llama_get_logits_ith(context_,1);
            if(!first||!second||llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL||
               llama_get_sampled_probs_ith(context_,-1)||llama_get_sampled_logits_ith(context_,-1))
                throw std::runtime_error("Width-two verification requires both complete original F32 CPU logit rows");
            checkpoint_candidates_.resize(std::size_t(count));
            for(llama_token id=0;id<count;++id) {
                if(!std::isfinite(first[id])||!std::isfinite(second[id]))
                    throw std::runtime_error("Non-finite width-two target logits");
                checkpoint_candidates_[id]={id,first[id],0.0f};
            }
            llama_token_data_array candidates{checkpoint_candidates_.data(),checkpoint_candidates_.size(),-1,false};
            llama_sampler_apply(sampler_,&candidates);
            if(candidates.selected<0||std::size_t(candidates.selected)>=candidates.size)
                throw std::runtime_error("Width-two target greedy selection failed");
            const auto target=candidates.data[candidates.selected].id;
            if(target==draft&&!llama_vocab_is_eog(vocabulary_,target)) {
                restored_logits_.assign(first,first+count);speculative_bonus_logits_.assign(second,second+count);
                restored_logits_active_=true;speculative_bonus_ready_=true;pending_=LLAMA_TOKEN_NULL;
                position_+=2;++speculative_stats_.accepted;
                draft_accepted=true;
                stage("speculative_width_two_target_completed_draft_accepted_bonus_pinned");
            }else {
                // The batched row is never emitted on rejection. Restore every
                // original state owner, then evaluate the pending token normally.
                cost_start=ProfileClock::now();restore_checkpoint_in_active_epoch();++speculative_stats_.rejected;
                restore_seconds=double(profile_elapsed_ns(cost_start))/1e9;
                stage("speculative_width_two_rejected_complete_state_restored");
            }
            boundary.complete();
            if(expert_hooks_.verified)expert_hooks_.verified(draft_accepted,capture_seconds,restore_seconds);
        }
        return next_once();
    }catch(...){failed_=true;throw;}
}
Token LlamaEngine::next_once() {
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
        const auto * logits = effective_logits();
        if (!logits || count <= 0) throw std::runtime_error("Missing logits");
        for (int i = 0; i < count; ++i) {
            if (!std::isfinite(logits[i])) throw std::runtime_error("Non-finite model logits");
        }
        if(logits_observer_) {
            if(llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL||llama_get_sampled_probs_ith(context_,-1)||llama_get_sampled_logits_ith(context_,-1))
                throw std::runtime_error("Logit observation requires the existing full-logit CPU greedy path");
            logits_observer_(logits,std::size_t(count));
        }
        stage("inference_before_sampling");
        if(restored_logits_active_) {
            checkpoint_candidates_.resize(std::size_t(count));
            for(llama_token id=0;id<count;++id)checkpoint_candidates_[id]={id,logits[id],0.0f};
            llama_token_data_array candidates{checkpoint_candidates_.data(),checkpoint_candidates_.size(),-1,false};
            llama_sampler_apply(sampler_,&candidates);
            if(candidates.selected<0||std::size_t(candidates.selected)>=candidates.size)
                throw std::runtime_error("Restored greedy sampler returned no selected token");
            pending_=candidates.data[candidates.selected].id;llama_sampler_accept(sampler_,pending_);
        }else pending_ = llama_sampler_sample(sampler_, context_, -1);
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
    if(checkpoint_stats_.enabled||speculative_stats_.enabled) {
        checkpoint_->discard();
        if(checkpoint_stats_.enabled)checkpoint_stats_.completed=checkpoint_stats_.captures>0&&checkpoint_stats_.captures==checkpoint_stats_.restores;
    }
    speculative_bonus_ready_=false;speculative_bonus_logits_.clear();
    speculative_committed_tokens_.clear();
    restored_logits_active_=false;restored_logits_.clear();checkpoint_reference_logits_.clear();checkpoint_candidates_.clear();
    ready_ = false;
    pending_ = LLAMA_TOKEN_NULL;
    prompt_.clear();
    boundary.complete();stage("inference_request_reset_completed");
    } catch (...) {failed_=true;throw;}
}

const float *LlamaEngine::effective_logits()const {
    return restored_logits_active_?restored_logits_.data():llama_get_logits_ith(context_,-1);
}
void LlamaEngine::enable_checkpoint_validation(std::function<void(std::uint64_t)> admit,
    std::function<std::uint32_t()> cursor,std::function<void(std::uint32_t,std::uint32_t,std::uint32_t)> compare) {
    require_healthy();
    if(producer_!=std::this_thread::get_id()||checkpoint_||ready_||!prompt_.empty()||prefill_tokens_!=4||llama_n_ctx(context_)!=256||!admit||!cursor||!compare||
       !gpu_begin_||!gpu_complete_||!gpu_retain_||!gpu_checkpoint_)
        throw std::invalid_argument("Checkpoint validation requires the original bounded context and complete owner hooks");
    checkpoint_=std::make_unique<ModelCheckpoint>(model_,context_);checkpoint_admit_=std::move(admit);
    checkpoint_route_cursor_=std::move(cursor);checkpoint_compare_routes_=std::move(compare);checkpoint_stats_.enabled=true;
}
void LlamaEngine::enable_prefix_reuse(std::function<void(std::uint64_t)> admit) {
    require_healthy();
    if(producer_!=std::this_thread::get_id()||checkpoint_||ready_||!prompt_.empty()||prefill_tokens_!=4||llama_n_ctx(context_)!=256||!admit||
       !gpu_begin_||!gpu_complete_||!gpu_retain_||!gpu_checkpoint_)
        throw std::invalid_argument("Prefix reuse requires one original bounded context and complete owner hooks");
    checkpoint_=std::make_unique<ModelCheckpoint>(model_,context_);checkpoint_admit_=std::move(admit);prefix_stats_.enabled=true;
}
void LlamaEngine::set_logits_observer(std::function<void(const float *,std::size_t)> observer) {
    require_healthy();
    if(producer_!=std::this_thread::get_id()||ready_||!prompt_.empty())
        throw std::invalid_argument("Completed-logit observation must be bound before tokenization on the original producer");
    logits_observer_=std::move(observer);
}
void LlamaEngine::enable_speculative_step_prototype(std::function<void(std::uint64_t)> admit) {
    require_healthy();
    if(producer_!=std::this_thread::get_id()||checkpoint_||ready_||!prompt_.empty()||prefill_tokens_!=4||llama_n_ctx(context_)!=256||!admit||
       !gpu_begin_||!gpu_complete_||!gpu_retain_||!gpu_checkpoint_)
        throw std::invalid_argument("Width-two prototype requires the original bounded context and complete owner hooks");
    checkpoint_=std::make_unique<ModelCheckpoint>(model_,context_);checkpoint_admit_=std::move(admit);speculative_stats_.enabled=true;
}
void LlamaEngine::enable_model_free_speculation(std::function<void(std::uint64_t)> admit) {
    if(selected_padded_cache_geometry().active_slots!=53)
        throw std::invalid_argument("Initial causal width-two qualification retains the 53-slot control");
    enable_speculative_step_prototype(std::move(admit));
    speculative_committed_tokens_.reserve(32);speculative_stats_.controller_enabled=true;
}
void LlamaEngine::enable_expert_aware_speculation(std::function<void(std::uint64_t)> admit,ExpertVerificationHooks hooks) {
    if(!hooks.before_process||!hooks.completed_ordinary||!hooks.choose||!hooks.verified)
        throw std::invalid_argument("Expert-aware speculation requires complete causal measurement hooks");
    enable_model_free_speculation(std::move(admit));expert_hooks_=std::move(hooks);
    speculative_stats_.expert_cost_enabled=true;
}
void LlamaEngine::capture_checkpoint_in_active_epoch() {
    guard();
    if(!checkpoint_||checkpoint_stats_.captures>=checkpoint_stats_.capture_positions.size())
        throw std::runtime_error("Checkpoint validation capture bound exhausted");
    if(llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL||llama_get_sampled_probs_ith(context_,-1)||llama_get_sampled_logits_ith(context_,-1))
        throw std::runtime_error("Checkpoint validation requires the existing full-logit CPU greedy sampler");
    CheckpointApplicationState state{request_epoch_,position_,pending_,ready_,prompt_};
    checkpoint_->capture(state,effective_logits(),std::size_t(llama_vocab_n_tokens(vocabulary_)),checkpoint_admit_,
        [&](const char *value){stage(value);},[&]{llama_synchronize(context_);gpu_checkpoint_();guard();});
    checkpoint_stats_.capture_positions[checkpoint_stats_.captures++]=position_;
    checkpoint_stats_.maximum_payload_bytes=std::max(checkpoint_stats_.maximum_payload_bytes,checkpoint_->payload_bytes());
    checkpoint_stats_.maximum_metadata_bytes=std::max<std::uint64_t>(checkpoint_stats_.maximum_metadata_bytes,checkpoint_->metadata_bytes());
}
void LlamaEngine::restore_checkpoint_in_active_epoch() {
    guard();const auto &saved=checkpoint_->restore(request_epoch_,[&](const char *value){stage(value);},
        [&]{llama_synchronize(context_);gpu_checkpoint_();guard();});
    if(saved.prompt!=prompt_)throw std::runtime_error("Restored checkpoint belongs to another prompt");
    position_=saved.position;pending_=saved.pending;ready_=saved.ready;
    restored_logits_=checkpoint_->logits();restored_logits_active_=true;llama_sampler_reset(sampler_);++checkpoint_stats_.restores;
}
void LlamaEngine::compare_checkpoint_logits() {
    const auto count=llama_vocab_n_tokens(vocabulary_);const auto *actual=effective_logits();
    if(!actual||count<=0||checkpoint_reference_logits_.size()!=std::size_t(count))throw std::runtime_error("Checkpoint continuation logits missing");
    for(int i=0;i<count;++i) {
        const double reference=checkpoint_reference_logits_[i],error=std::abs(double(actual[i])-reference);
        if(!std::isfinite(reference)||!std::isfinite(actual[i])||error>1e-5+1e-5*std::abs(reference))
            throw std::runtime_error("Restored complete-model logits differ from original operations");
        checkpoint_stats_.maximum_absolute_logit_error=std::max(checkpoint_stats_.maximum_absolute_logit_error,error);
    }
}
void LlamaEngine::compare_checkpoint_routes(std::uint32_t first,std::uint32_t first_end,std::uint32_t second) {
    const auto end=checkpoint_route_cursor_();
    if(first_end<first||end<second||first_end-first!=end-second)throw std::runtime_error("Restored route process count differs");
    checkpoint_compare_routes_(first,second,first_end-first);checkpoint_stats_.route_rows_compared+=first_end-first;
}
Token LlamaEngine::validate_next_checkpoint() {
    require_healthy();if(!ready_)throw std::logic_error("Prefill required before checkpoint validation");
    try {
        {GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);capture_checkpoint_in_active_epoch();boundary.complete();}
        const auto first=checkpoint_route_cursor_();const auto reference=next_once();const auto first_end=checkpoint_route_cursor_();
        const auto *values=effective_logits();const auto count=llama_vocab_n_tokens(vocabulary_);
        if(!values||count<=0)throw std::runtime_error("Checkpoint target reference logits unavailable");
        checkpoint_reference_logits_.assign(values,values+count);
        {GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);restore_checkpoint_in_active_epoch();boundary.complete();}
        const auto second=checkpoint_route_cursor_();const auto actual=next_once();
        if(reference.id!=actual.id||reference.piece!=actual.piece||reference.end_of_generation!=actual.end_of_generation)
            throw std::runtime_error("Restored greedy continuation token or emitted bytes differ");
        compare_checkpoint_logits();compare_checkpoint_routes(first,first_end,second);
        ++checkpoint_stats_.next_replays;stage("model_checkpoint_next_replay_verified_emitted_once");return actual;
    }catch(...){failed_=true;throw;}
}

} // namespace qwen_app
