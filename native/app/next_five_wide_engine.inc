// SPDX-License-Identifier: MIT
namespace qwen_app {
Token LlamaEngine::next_with_three_drafts(const std::array<llama_token,3>&drafts){
    require_healthy();const auto count=llama_vocab_n_tokens(vocabulary_);
    if(!speculative_stats_.enabled||!ready_||pending_==LLAMA_TOKEN_NULL||llama_vocab_is_eog(vocabulary_,pending_)||
       speculative_bonus_ready_||wide_bonus_remaining()||count<=0||count>262144||std::uint64_t(position_)+4>llama_n_ctx(context_)||
       speculative_stats_.attempts>=32||llama_n_rs_seq(context_)!=3)
        throw std::invalid_argument("Width-four requires its complete three-token rollback owner");
    for(auto d:drafts)if(d<0||d>=count)throw std::invalid_argument("Draft vocabulary bounds differ");
    try{
        guard();{
            GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);
            if(llama_memory_seq_pos_max(llama_get_memory(context_),0)!=position_-1)throw std::runtime_error("Wide pending position differs");
            ++speculative_stats_.attempts;++compact_captures;
            const llama_token tokens[]={pending_,drafts[0],drafts[1],drafts[2]};process_batch_once(tokens,4,position_);
            const float*rows[4]{};for(unsigned r=0;r<4;++r){rows[r]=llama_get_logits_ith(context_,int(r));if(!rows[r])throw std::runtime_error("Missing complete wide target row");for(int i=0;i<count;++i)if(!std::isfinite(rows[r][i]))throw std::runtime_error("Nonfinite wide target row");}
            if(llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL||llama_get_sampled_probs_ith(context_,-1)||llama_get_sampled_logits_ith(context_,-1))throw std::runtime_error("Wide verification requires original CPU greedy sampling");
            bool accepted=true;checkpoint_candidates_.resize(std::size_t(count));
            for(unsigned r=0;r<3;++r){
                for(llama_token id=0;id<count;++id)checkpoint_candidates_[id]={id,rows[r][id],0.f};
                llama_token_data_array candidates{checkpoint_candidates_.data(),checkpoint_candidates_.size(),-1,false};llama_sampler_apply(sampler_,&candidates);
                if(candidates.selected<0||std::size_t(candidates.selected)>=candidates.size)throw std::runtime_error("Wide greedy selection failed");
                const auto target=candidates.data[candidates.selected].id;accepted=accepted&&target==drafts[r]&&!llama_vocab_is_eog(vocabulary_,target);
            }
            restored_logits_.assign(rows[0],rows[0]+count);restored_logits_active_=true;
            if(accepted){
                wide_logits_.resize(3);wide_cursor_=0;for(unsigned r=1;r<4;++r)wide_logits_[r-1].assign(rows[r],rows[r]+count);
                position_+=4;pending_=LLAMA_TOKEN_NULL;++speculative_stats_.accepted;stage("wide_four_target_rows_accepted_three_bonus_rows_pinned");
            }else{
                const auto memory=llama_get_memory(context_);if(!llama_memory_seq_rm(memory,0,position_+1,-1)||llama_memory_seq_pos_max(memory,0)!=position_)throw std::runtime_error("Wide complete hybrid rollback failed; retain owner");
                ++position_;pending_=LLAMA_TOKEN_NULL;++speculative_stats_.rejected;++compact_rejections;stage("wide_rejection_three_tokens_all_memory_rewound");
            }
            boundary.complete();
        }return next_once();
    }catch(...){failed_=true;throw;}
}
}
