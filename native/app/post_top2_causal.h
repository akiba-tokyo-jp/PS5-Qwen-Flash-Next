// SPDX-License-Identifier: MIT
#pragma once
#include <llama_engine.h>
#include <model_free_draft.h>
#include "expert_routing_policy.h"
namespace qwen_app {
// Same single-latest committed-history proposals as the selected normal app.
// The explicit attempt cap is independent of width (one pending plus one draft).
class PostTop2CausalEngine final:public Engine {
    LlamaEngine&e_;llama_model*m_;bool force_,bonus_=false;
    unsigned limit_,attempts_=0;std::vector<llama_token>prompt_,history_;
public:
    std::uint64_t causal_proposals=0;
    PostTop2CausalEngine(LlamaEngine&e,llama_model*m,llama_context*c,bool force,unsigned cap):e_(e),m_(m),force_(force),limit_(cap){
        if(!m||!c||llama_n_ctx(c)!=256||(cap!=6&&cap!=8&&cap!=12))throw std::invalid_argument("Bounded current-controller comparison required");
        prompt_.resize(64);history_.reserve(32);
    }
    std::uint32_t tokenize(const std::string&s)override{
        const int n=llama_tokenize(llama_model_get_vocab(m_),s.data(),int(s.size()),prompt_.data(),64,true,true);
        if(n<=0||n>64)throw std::runtime_error("Causal prompt exceeds its admitted bound");
        prompt_.resize(n);const auto got=e_.tokenize(s);if(got!=unsigned(n))throw std::runtime_error("Causal prompt metadata differs");return got;
    }
    void prefill(std::uint32_t n)override{e_.prefill(n);}
    Token next()override{
        if(history_.size()>=32)throw std::runtime_error("Causal output exceeds its bound");
        llama_token draft=LLAMA_TOKEN_NULL;
        if(!bonus_&&!history_.empty()&&attempts_<limit_&&history_.size()<=30){
            if(force_)draft=llama_vocab_eos(llama_model_get_vocab(m_));
            else {const auto p=propose_model_free_token(prompt_.data(),prompt_.size(),history_.data(),history_.size(),
                llama_vocab_n_tokens(llama_model_get_vocab(m_)),DraftEvidence::single_latest);
                if(p.found&&!llama_vocab_is_eog(llama_model_get_vocab(m_),p.token))draft=p.token;}
        }
        const auto before=e_.speculative_step_stats();if(!bonus_)qwen_app_routing_event_begin();bonus_=false;
        auto token=draft==LLAMA_TOKEN_NULL?e_.next():e_.next_with_one_draft(draft);
        if(draft!=LLAMA_TOKEN_NULL){const auto after=e_.speculative_step_stats();++attempts_;++causal_proposals;
            if(after.attempts!=before.attempts+1||after.accepted+after.rejected!=before.accepted+before.rejected+1)
                throw std::runtime_error("Complete causal target decision required");
            bonus_=after.accepted==before.accepted+1;}
        if(!token.end_of_generation)history_.push_back(token.id);return token;
    }
    void finish()override{e_.finish();}
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override{return e_.expert_cache_metrics();}
};
}
