// SPDX-License-Identifier: MIT
#pragma once
#include <llama_engine.h>
#include <model_free_draft.h>
#include "expert_routing_policy.h"
namespace qwen_app {
class CausalExpertSharingEngine final:public Engine {
    LlamaEngine&e_;llama_model*m_;llama_context*c_;bool enabled_,bonus_=false;
    std::vector<llama_token>prompt_,history_;unsigned attempts_=0;
public:
    std::uint64_t causal_proposals=0;
    CausalExpertSharingEngine(LlamaEngine&e,llama_model*m,llama_context*c,bool enabled):e_(e),m_(m),c_(c),enabled_(enabled){
        if(!m||!c||llama_n_ctx(c)!=256||e.prefill_batch_tokens()!=4)throw std::invalid_argument("Original bounded sharing context required");
        prompt_.resize(64);history_.reserve(32);
    }
    std::uint32_t tokenize(const std::string&s)override{
        const auto n=llama_tokenize(llama_model_get_vocab(m_),s.data(),int(s.size()),prompt_.data(),64,true,true);
        if(n<=0||n>64)throw std::runtime_error("Causal prompt exceeds its admitted bound");
        prompt_.resize(std::size_t(n));const auto got=e_.tokenize(s);
        if(got!=std::uint32_t(n))throw std::runtime_error("Causal prompt metadata differs");return got;
    }
    void prefill(std::uint32_t n)override{e_.prefill(n);}
    Token next()override{
        if(history_.size()>=32)throw std::runtime_error("Causal output exceeds its bound");
        llama_token draft=LLAMA_TOKEN_NULL;
        if(enabled_&&!bonus_&&!history_.empty()&&attempts_<8&&history_.size()<=30){
            const auto p=propose_model_free_token(prompt_.data(),prompt_.size(),history_.data(),history_.size(),
                std::size_t(llama_vocab_n_tokens(llama_model_get_vocab(m_))),DraftEvidence::single_latest);
            if(p.found&&!llama_vocab_is_eog(llama_model_get_vocab(m_),p.token)){draft=p.token;++causal_proposals;}
        }
        const auto before=e_.speculative_step_stats();
        if(!bonus_)qwen_app_routing_event_begin();bonus_=false;
        auto token=draft==LLAMA_TOKEN_NULL?e_.next():e_.next_with_one_draft(draft);
        if(draft!=LLAMA_TOKEN_NULL){
            const auto done=e_.speculative_step_stats();++attempts_;
            if(done.attempts!=before.attempts+1||done.accepted+done.rejected!=before.accepted+before.rejected+1)
                throw std::runtime_error("Every causal verification requires a complete decision");
            bonus_=done.accepted==before.accepted+1;
        }
        if(!token.end_of_generation)history_.push_back(token.id);return token;
    }
    void finish()override{e_.finish();}
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override{return e_.expert_cache_metrics();}
};
using RepeatedExpertQ2SpeculativeEngine=CausalExpertSharingEngine;
}
