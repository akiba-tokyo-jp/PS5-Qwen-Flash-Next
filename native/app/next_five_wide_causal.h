// SPDX-License-Identifier: MIT
#pragma once
#include <llama_engine.h>
#include <model_free_draft.h>
#include "next_five_policy.h"
extern "C" void qwen_app_routing_event_begin();
namespace qwen_app {
class WideHistoryEngine final:public Engine {
    LlamaEngine&e_;llama_model*m_;bool force_;std::vector<llama_token>prompt_,history_;unsigned attempts_=0;bool pair_bonus_=false;
public:
    std::uint64_t causal_proposals=0,wide_proposals=0;
    WideHistoryEngine(LlamaEngine&e,llama_model*m,llama_context*,bool force):e_(e),m_(m),force_(force){prompt_.resize(64);history_.reserve(32);}
    std::uint32_t tokenize(const std::string&s)override{
        auto n=llama_tokenize(llama_model_get_vocab(m_),s.data(),int(s.size()),prompt_.data(),64,true,true);if(n<=0||n>64)throw std::runtime_error("Bounded wide prompt required");prompt_.resize(n);auto count=e_.tokenize(s);if(count!=unsigned(n))throw std::runtime_error("Wide prompt differs");return count;
    }
    void prefill(std::uint32_t n)override{e_.prefill(n);}
    Token next()override{
        const bool queued=pair_bonus_||e_.wide_bonus_remaining();pair_bonus_=false;
        if(!queued)qwen_app_routing_event_begin();
        std::array<llama_token,3>drafts{};bool wide=false;llama_token draft=LLAMA_TOKEN_NULL;
        const auto vocab=llama_model_get_vocab(m_);const auto n=llama_vocab_n_tokens(vocab);
        if(!queued&&!history_.empty()&&attempts_<6&&history_.size()<=30){
            if(qwen_next_variant()==6&&history_.size()<=28){
                if(force_){drafts.fill(llama_vocab_eos(vocab));wide=true;}
                else{auto hypothetical=history_;wide=true;for(unsigned i=0;i<3;++i){auto p=propose_model_free_token(prompt_.data(),prompt_.size(),hypothetical.data(),hypothetical.size(),n,DraftEvidence::single_latest);if(!p.found||llama_vocab_is_eog(vocab,p.token)){wide=false;break;}drafts[i]=p.token;hypothetical.push_back(p.token);}}
            }
            if(!wide){if(force_)draft=llama_vocab_eos(vocab);else{auto p=propose_model_free_token(prompt_.data(),prompt_.size(),history_.data(),history_.size(),n,DraftEvidence::consistent_pair);if(p.found&&!llama_vocab_is_eog(vocab,p.token))draft=p.token;}}
        }
        auto before=e_.speculative_step_stats();auto result=wide?e_.next_with_three_drafts(drafts):draft!=LLAMA_TOKEN_NULL?e_.next_with_one_draft(draft):e_.next();
        if(wide||draft!=LLAMA_TOKEN_NULL){++attempts_;++causal_proposals;if(wide)++wide_proposals;auto after=e_.speculative_step_stats();if(after.attempts!=before.attempts+1||after.accepted+after.rejected!=before.accepted+before.rejected+1)throw std::runtime_error("Wide target decision differs");pair_bonus_=!wide&&after.accepted==before.accepted+1;}
        if(!result.end_of_generation)history_.push_back(result.id);return result;
    }
    void finish()override{e_.finish();}
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override{return e_.expert_cache_metrics();}
};
}
