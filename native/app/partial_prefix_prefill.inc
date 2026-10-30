// SPDX-License-Identifier: MIT
// Scoped replacement of LlamaEngine::prefill; the context and checkpoint ABI
// remain unchanged. The caller configures one original producer between groups.
void LlamaEngine::prefill(std::uint32_t context_tokens) {
    require_healthy();
    if(speculative_stats_.enabled&&(ready_||speculative_bonus_ready_))
        throw std::invalid_argument("A speculative request cannot prefill before cleanup");
    if(prompt_.empty()||prompt_.size()>=context_tokens||context_tokens>llama_n_ctx(context_))
        throw std::invalid_argument("Invalid context admission");
    try {
        guard();GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);
        stage("inference_before_prefill");
        const auto requested=prompt_;
        const auto reusable=qwen_app_partial_prefix_enabled()?std::min<std::size_t>(16,prompt_.size()):prompt_.size();
        const std::vector<llama_token>prefix(prompt_.begin(),prompt_.begin()+reusable);
        bool hit=false;
        if(prefix_stats_.enabled&&checkpoint_->matches_complete_prompt(prefix)) {
            prompt_=prefix;
            {ProfileScope timing(prefix_stats_.restore_ns);
                checkpoint_->rebind_complete_prompt(request_epoch_,prefix);
                restore_checkpoint_in_active_epoch();}
            if(!ready_||pending_!=LLAMA_TOKEN_NULL||position_!=llama_pos(reusable))
                throw std::runtime_error("Restored common prefix positions differ");
            prompt_=requested;++prefix_stats_.restores;prefix_stats_.request_hit=true;
            prefix_stats_.last_reused_prompt_tokens=std::uint32_t(reusable);hit=true;
            stage("inference_common_prefix_restored_completed");
            if(reusable==requested.size()){boundary.complete();return;}
        }
        if(!hit) {
            prefix_stats_.request_hit=false;prefix_stats_.last_reused_prompt_tokens=0;
            if(prefix_stats_.enabled&&qwen_app_partial_prefix_enabled())checkpoint_->discard();
            llama_memory_clear(llama_get_memory(context_),true);llama_sampler_reset(sampler_);
            position_=0;pending_=LLAMA_TOKEN_NULL;
        }
        ready_=false;inside_prefill_=true;
        for(std::size_t i=std::size_t(position_);i<prompt_.size();) {
            const auto count=std::uint32_t(std::min<std::size_t>(prefill_tokens_,prompt_.size()-i));
            process_batch(prompt_.data()+i,count,position_);position_+=count;i+=count;
            if(prefix_stats_.enabled&&qwen_app_partial_prefix_enabled()&&!checkpoint_->saved()&&position_==16) {
                // The saved application prompt describes exactly the tensors
                // captured at this boundary, independently of the later suffix.
                const auto full=prompt_;prompt_.resize(16);ready_=true;
                {ProfileScope timing(prefix_stats_.capture_ns);capture_checkpoint_in_active_epoch();}
                ++prefix_stats_.captures;prompt_=full;ready_=false;
                stage("inference_common_prefix_capture_completed");
            }
        }
        inside_prefill_=false;
        if(prefix_stats_.enabled&&!qwen_app_partial_prefix_enabled()) {
            ready_=true;{ProfileScope timing(prefix_stats_.capture_ns);capture_checkpoint_in_active_epoch();}
            ++prefix_stats_.captures;
        }
        boundary.complete();ready_=true;stage("inference_prefill_completed");
    }catch(...){inside_prefill_=false;failed_=true;throw;}
}
