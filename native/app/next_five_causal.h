// SPDX-License-Identifier: MIT
#pragma once
#include <llama_engine.h>
#include <model_free_draft.h>
#include "next_five_policy.h"
extern "C" void qwen_app_routing_event_begin();
namespace qwen_app {
// Proposal evidence is committed history only. The adaptive budget stops after
// two consecutive rejected proposals and never changes target verification.
class NextFiveCausalEngine final:public Engine {
    LlamaEngine&e_;llama_model*m_;bool force_,bonus_=false;
    std::vector<llama_token>prompt_,history_;unsigned attempts_=0,rejections_=0;
public:
    std::uint64_t causal_proposals=0;
    NextFiveCausalEngine(LlamaEngine&e,llama_model*m,llama_context*,bool force):e_(e),m_(m),force_(force){prompt_.resize(64);history_.reserve(32);}
    std::uint32_t tokenize(const std::string&s)override{
        auto n=llama_tokenize(llama_model_get_vocab(m_),s.data(),int(s.size()),prompt_.data(),64,true,true);
        if(n<=0||n>64)throw std::runtime_error("Bounded causal prompt required");prompt_.resize(n);auto got=e_.tokenize(s);if(got!=unsigned(n))throw std::runtime_error("Causal prompt differs");return got;
    }
    void prefill(std::uint32_t n)override{e_.prefill(n);}
    Token next()override{
        llama_token draft=LLAMA_TOKEN_NULL;const bool extended=qwen_next_variant()==4;
        if(!bonus_&&!history_.empty()&&attempts_<(extended?32u:6u)&&history_.size()<=30&&(!extended||force_||rejections_<2)){
            if(force_)draft=llama_vocab_eos(llama_model_get_vocab(m_));
            else{auto p=propose_model_free_token(prompt_.data(),prompt_.size(),history_.data(),history_.size(),llama_vocab_n_tokens(llama_model_get_vocab(m_)),DraftEvidence::consistent_pair);if(p.found&&!llama_vocab_is_eog(llama_model_get_vocab(m_),p.token))draft=p.token;}
        }
        auto before=e_.speculative_step_stats();if(!bonus_)qwen_app_routing_event_begin();bonus_=false;
        auto token=draft==LLAMA_TOKEN_NULL?e_.next():e_.next_with_one_draft(draft);
        if(draft!=LLAMA_TOKEN_NULL){++attempts_;++causal_proposals;auto after=e_.speculative_step_stats();
            if(after.attempts!=before.attempts+1||after.accepted+after.rejected!=before.accepted+before.rejected+1)throw std::runtime_error("Complete target decision required");
            bonus_=after.accepted==before.accepted+1;rejections_=bonus_?0:rejections_+1;}
        if(!token.end_of_generation)history_.push_back(token.id);return token;
    }
    void finish()override{e_.finish();}
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override{return e_.expert_cache_metrics();}
};
}
