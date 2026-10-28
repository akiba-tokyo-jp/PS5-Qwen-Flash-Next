// SPDX-License-Identifier: MIT
#pragma once
#include "llama_engine.h"
#include "adaptive_draft_depth.h"
#include "model_free_span.h"
#include "wide_draft_control.h"
#include "profile_clock.h"
namespace qwen_app {
enum class CausalWideMode {ordinary,fixed_two,fixed_four,adaptive};
class CausalWideEngine final:public Engine{
    LlamaEngine&e_;llama_context*c_;CausalWideMode mode_;
    std::vector<std::int32_t> prompt_,history_;
    AdaptiveDraftDepth controller_;
    unsigned queue_=0,attempts_=0,maximum_attempts_;
    unsigned pending_width_=0,pending_committed_=0;
    double pending_seconds_=0;
    std::uint64_t decisions_=0,decision_ns_=0;
public:
    std::int32_t ending_minimum=-1,ending_maximum=-1;
    CausalWideEngine(LlamaEngine&e,llama_context*c,CausalWideMode m,std::vector<std::int32_t> prompt,unsigned attempts):
        e_(e),c_(c),mode_(m),prompt_(std::move(prompt)),maximum_attempts_(attempts){
        if(!c||prompt_.empty()||prompt_.size()>64||!attempts||attempts>8)
            throw std::invalid_argument("Bounded causal wide engine inputs required");
        history_.reserve(32);
    }
    std::uint32_t tokenize(const std::string&s)override{return e_.tokenize(s);}
    void prefill(std::uint32_t n)override{e_.prefill(n);}
    Token next()override{
        if(history_.size()>=32)throw std::runtime_error("Causal wide output bound exceeded");
        if(queue_){const auto start=ProfileClock::now();auto token=e_.next();
            pending_seconds_+=double(profile_elapsed_ns(start))/1e9;--queue_;
            if(!token.end_of_generation){history_.push_back(token.id);++pending_committed_;}
            if(!queue_||token.end_of_generation){controller_.observe(pending_width_,pending_committed_,pending_seconds_,true);
                pending_width_=pending_committed_=0;pending_seconds_=0;queue_=0;}
            return token;}
        const auto decision_start=ProfileClock::now();unsigned width=1;
        std::array<std::int32_t,3> drafts{};
        const auto vocabulary=llama_model_get_vocab(llama_get_model(c_));
        if(mode_!=CausalWideMode::ordinary&&!history_.empty()&&attempts_<maximum_attempts_){
            const auto one=propose_model_free_token(prompt_.data(),prompt_.size(),history_.data(),history_.size(),
                std::size_t(llama_vocab_n_tokens(vocabulary)),DraftEvidence::consistent_pair);
            const auto span=propose_model_free_span(prompt_.data(),prompt_.size(),history_.data(),history_.size(),
                std::size_t(llama_vocab_n_tokens(vocabulary)));
            unsigned proposals=0;
            if(one.found&&!llama_vocab_is_eog(vocabulary,one.token)){drafts[0]=one.token;proposals=1;}
            if(span.found){bool finite=true;for(auto id:span.tokens)finite=finite&&!llama_vocab_is_eog(vocabulary,id);
                if(finite){drafts=span.tokens;proposals=3;}}
            const auto remaining=unsigned(32-history_.size());
            if(mode_==CausalWideMode::adaptive)width=controller_.choose(proposals,remaining,true);
            else if(mode_==CausalWideMode::fixed_two&&proposals&&remaining>=2)width=2;
            else if(mode_==CausalWideMode::fixed_four&&proposals==3&&remaining>=4)width=4;
        }
        ++decisions_;decision_ns_+=profile_elapsed_ns(decision_start);
        const auto before=e_.speculative_step_stats();const auto calls=e_.timing_stats().process_calls;
        const auto started=ProfileClock::now();Token token;
        if(width==4){wide_draft_control.arm(&e_,drafts);token=e_.next_with_one_draft(drafts[0]);}
        else if(width==2)token=e_.next_with_one_draft(drafts[0]);else token=e_.next();
        const auto elapsed=double(profile_elapsed_ns(started))/1e9;
        const auto after=e_.speculative_step_stats();
        if(width>1){++attempts_;if(after.attempts!=before.attempts+1)
            throw std::runtime_error("An actual causal target verification is required");
            queue_=after.accepted==before.accepted+1?width-1:0;
            if(queue_){pending_width_=width;pending_committed_=token.end_of_generation?0:1;pending_seconds_=elapsed;}
            else controller_.observe(width,1,elapsed,true);
        }else if(e_.timing_stats().process_calls>calls)controller_.observe(1,1,elapsed,true);
        if(!token.end_of_generation)history_.push_back(token.id);return token;
    }
    void finish()override{const auto memory=llama_get_memory(c_);ending_minimum=llama_memory_seq_pos_min(memory,0);
        ending_maximum=llama_memory_seq_pos_max(memory,0);e_.finish();}
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override{return e_.expert_cache_metrics();}
    std::uint64_t decisions()const{return decisions_;}
    std::uint64_t decision_ns()const{return decision_ns_;}
};
}
