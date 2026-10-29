// SPDX-License-Identifier: MIT
#pragma once
#include <llama_engine.h>
#include <completed_expert_routes.h>
#include <model_free_draft.h>
#include <mapped_source.h>
namespace qwen_app {
// An explicitly scoped adapter for the sealed all-Q2 model. It uses the
// existing complete-state prototype, leaving the BF16 controller guard intact.
// Only past committed tokens and completed route observations propose a draft.
class ExpertQ2SpeculativeEngine final:public Engine {
    LlamaEngine&e_;llama_model*m_;llama_context*c_;bool enabled_,bonus_=false;
    std::vector<llama_token>prompt_,history_;
    OnlineExpertVerification cost_;unsigned attempts_=0;llama_token forced_rejection_=-1;unsigned forced_at_=2;
public:
    std::uint64_t causal_proposals=0,calibration_attempts=0,ordinary_observations=0;
    std::int32_t ending_minimum=-1,ending_maximum=-1;
    ExpertQ2SpeculativeEngine(LlamaEngine&e,llama_model*m,llama_context*c,bool enabled,llama_token forced_rejection=-1,unsigned forced_at=2):e_(e),m_(m),c_(c),enabled_(enabled),forced_rejection_(forced_rejection),forced_at_(forced_at){
        if(!m||!c||llama_n_ctx(c)!=256||e.prefill_batch_tokens()!=4||forced_at<1||forced_at>30)
            throw std::invalid_argument("Q2 speculation requires the exact admitted retained context");
        history_.reserve(32);prompt_.resize(64);
    }
    std::uint32_t tokenize(const std::string&s)override{
        const auto n=llama_tokenize(llama_model_get_vocab(m_),s.data(),int(s.size()),prompt_.data(),64,true,true);
        if(n<=0||n>64)throw std::runtime_error("Q2 causal prompt exceeds the fixed scope");
        prompt_.resize(std::size_t(n));const auto got=e_.tokenize(s);
        if(got!=std::uint32_t(n))throw std::runtime_error("Q2 causal token metadata differs");return got;
    }
    void prefill(std::uint32_t n)override{e_.prefill(n);}
    Token next()override{
        if(history_.size()>=32)throw std::runtime_error("Q2 causal output bound exceeded");
        unsigned width=1;llama_token draft=-1;const auto pending=history_.empty()?LLAMA_TOKEN_NULL:history_.back();
        if(enabled_&&!bonus_&&pending!=LLAMA_TOKEN_NULL&&attempts_<1&&history_.size()<=30){
            const auto proposal=propose_model_free_token(prompt_.data(),prompt_.size(),history_.data(),history_.size(),
                std::size_t(llama_vocab_n_tokens(llama_model_get_vocab(m_))),DraftEvidence::consistent_pair);
            if(proposal.found&&!llama_vocab_is_eog(llama_model_get_vocab(m_),proposal.token)){
                ++causal_proposals;draft=proposal.token;width=cost_.choose(pending,draft);
            }
        }
        // A separately labeled, untimed negative control. It never supplies
        // draft tokens to the causal speed arms.
        if(forced_rejection_>=0&&history_.size()==forced_at_&&attempts_==0){width=2;draft=forced_rejection_;}
        const auto before=e_.timing_stats();const auto source=native_model_source_stats().read_ns;
        const auto stats=e_.speculative_step_stats();const bool sampled_bonus=bonus_;bonus_=false;
        auto token=width==2?e_.next_with_one_draft(draft):e_.next();
        const auto after=e_.timing_stats();const auto done=e_.speculative_step_stats();
        if(width==2){
            ++attempts_;++calibration_attempts;
            if(done.attempts!=stats.attempts+1||done.accepted+done.rejected!=stats.accepted+stats.rejected+1)
                throw std::runtime_error("Q2 width-two target verification did not complete");
            bonus_=done.accepted==stats.accepted+1;
        }else if(enabled_&&!sampled_bonus&&pending!=LLAMA_TOKEN_NULL&&after.process_calls==before.process_calls+1){
            const auto elapsed=after.process_ns-before.process_ns,io=native_model_source_stats().read_ns-source;
            if(!elapsed||io>elapsed)throw std::runtime_error("Q2 causal costs are not completed observations");
            cost_.observe(pending,last_completed_single_token_routes(),double(elapsed)/1e9,double(io)/1e9);++ordinary_observations;
        }
        if(!token.end_of_generation)history_.push_back(token.id);return token;
    }
    void finish()override{
        const auto memory=llama_get_memory(c_);ending_minimum=llama_memory_seq_pos_min(memory,0);ending_maximum=llama_memory_seq_pos_max(memory,0);
        e_.finish();
    }
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override{return e_.expert_cache_metrics();}
};
}
