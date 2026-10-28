#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Generate isolated width-four target verification without changing class ABI."""
from build_speculative_batch_probe import once


def generate(text):
    text='#include "wide_draft_control.h"\nnamespace qwen_app { WideDraftControl wide_draft_control; }\n'+text
    text=once(text,'        restored_logits_=std::move(speculative_bonus_logits_);restored_logits_active_=true;\n        speculative_bonus_ready_=false;pending_=LLAMA_TOKEN_NULL;++speculative_stats_.queued_bonus_samples;',
        '''        pop_verified_logits(speculative_bonus_logits_,restored_logits_,std::size_t(llama_vocab_n_tokens(vocabulary_)),speculative_bonus_ready_);
        restored_logits_active_=true;pending_=LLAMA_TOKEN_NULL;++speculative_stats_.queued_bonus_samples;''')
    marker='    try {\n        guard();\n        {\n            GpuBoundary boundary(gpu_begin_,gpu_complete_,gpu_retain_);\n            ++speculative_stats_.attempts;'
    text=once(text,marker,'''    const auto wide_plan=wide_draft_control.consume(this,draft);
    if(wide_plan.width!=2&&wide_plan.width!=4)throw std::invalid_argument("Only qualified bounded draft widths are eligible");
    if(std::uint64_t(position_)+wide_plan.width>llama_n_ctx(context_))
        throw std::invalid_argument("Wide verification exceeds the original context");
    for(unsigned i=0;i<wide_plan.width-1;++i)
        if(wide_plan.drafts[i]<0||wide_plan.drafts[i]>=count||llama_vocab_is_eog(vocabulary_,wide_plan.drafts[i]))
            throw std::invalid_argument("Wide verification cannot draft an end token");
'''+marker)
    begin=text.index('            const llama_token pair[]={pending_,draft};')
    end=text.index('                stage("speculative_width_two_target_completed_draft_accepted_bonus_pinned");',begin)
    end+=len('                stage("speculative_width_two_target_completed_draft_accepted_bonus_pinned");')
    text=text[:begin]+'''            const std::array<llama_token,4> pair{{pending_,wide_plan.drafts[0],wide_plan.drafts[1],wide_plan.drafts[2]}};
            process_batch_once(pair.data(),wide_plan.width,position_);
            if(llama_get_sampled_token_ith(context_,-1)!=LLAMA_TOKEN_NULL||
               llama_get_sampled_probs_ith(context_,-1)||llama_get_sampled_logits_ith(context_,-1))
                throw std::runtime_error("Wide verification requires original full F32 CPU logits");
            std::array<const float *,4> rows{};
            for(unsigned row=0;row<wide_plan.width;++row) {
                rows[row]=llama_get_logits_ith(context_,int(row));
                if(!rows[row])throw std::runtime_error("A complete wide target row is missing");
                for(llama_token id=0;id<count;++id)if(!std::isfinite(rows[row][id]))
                    throw std::runtime_error("Non-finite wide target logits");
            }
            unsigned accepted_prefix=0;
            checkpoint_candidates_.resize(std::size_t(count));
            for(unsigned row=0;row<wide_plan.width-1;++row) {
                for(llama_token id=0;id<count;++id)checkpoint_candidates_[id]={id,rows[row][id],0.0f};
                llama_token_data_array candidates{checkpoint_candidates_.data(),checkpoint_candidates_.size(),-1,false};
                llama_sampler_apply(sampler_,&candidates);
                if(candidates.selected<0||std::size_t(candidates.selected)>=candidates.size)
                    throw std::runtime_error("Wide target greedy selection failed");
                const auto target=candidates.data[candidates.selected].id;
                if(target!=wide_plan.drafts[row]||llama_vocab_is_eog(vocabulary_,target))break;
                ++accepted_prefix;
            }
            if(wide_plan.width==4)wide_draft_control.decision(accepted_prefix);
            if(accepted_prefix==wide_plan.width-1) {
                restored_logits_.assign(rows[0],rows[0]+count);speculative_bonus_logits_.clear();
                speculative_bonus_logits_.reserve(std::size_t(count)*(wide_plan.width-1));
                for(unsigned row=1;row<wide_plan.width;++row)
                    speculative_bonus_logits_.insert(speculative_bonus_logits_.end(),rows[row],rows[row]+count);
                restored_logits_active_=true;speculative_bonus_ready_=true;pending_=LLAMA_TOKEN_NULL;
                position_+=wide_plan.width;++speculative_stats_.accepted;draft_accepted=true;
                stage("speculative_bounded_target_completed_all_drafts_accepted_bonus_pinned");'''+text[end:]
    # Partial prefixes restore the complete pre-batch state and use the ordinary
    # target. No rejected suffix or unverified token is ever emitted.
    return text
