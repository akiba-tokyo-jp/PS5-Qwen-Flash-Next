// SPDX-License-Identifier: MIT
#pragma once
#include <llama_engine.h>
#include <model_free_draft.h>
#include "expert_routing_policy.h"
extern "C" int32_t qwen_post_mtp_draft();
namespace qwen_app {
// Stateless matched-head proposals are never published without target verification.
class PostTop2MtpCausalEngine final:public Engine {
 LlamaEngine&e_;llama_model*m_;bool candidate_,force_,bonus_=false;unsigned attempts_=0;
 std::vector<llama_token>prompt_,history_;
public:
 std::uint64_t causal_proposals=0,MTP_proposals=0;
 PostTop2MtpCausalEngine(LlamaEngine&e,llama_model*m,llama_context*c,bool force,bool candidate):e_(e),m_(m),candidate_(candidate),force_(force){
  if(!m||!c||llama_n_ctx(c)!=256)throw std::invalid_argument("Current bounded MTP controller required");prompt_.resize(64);history_.reserve(32);}
 std::uint32_t tokenize(const std::string&s)override{const int n=llama_tokenize(llama_model_get_vocab(m_),s.data(),int(s.size()),prompt_.data(),64,true,true);if(n<=0||n>64)throw std::runtime_error("MTP prompt bound exceeded");prompt_.resize(n);const auto got=e_.tokenize(s);if(got!=unsigned(n))throw std::runtime_error("MTP prompt metadata differs");return got;}
 void prefill(std::uint32_t n)override{e_.prefill(n);}
 Token next()override{
  if(history_.size()>=32)throw std::runtime_error("MTP output bound exceeded");llama_token draft=LLAMA_TOKEN_NULL;bool mtp=false;
  if(!bonus_&&!history_.empty()&&history_.size()<=30&&attempts_<32){
   if(force_&&(!candidate_?attempts_<6:attempts_==0))draft=llama_vocab_eos(llama_model_get_vocab(m_));
   else if(attempts_<6){const auto p=propose_model_free_token(prompt_.data(),prompt_.size(),history_.data(),history_.size(),llama_vocab_n_tokens(llama_model_get_vocab(m_)),DraftEvidence::single_latest);if(p.found&&!llama_vocab_is_eog(llama_model_get_vocab(m_),p.token))draft=p.token;}
   if(candidate_&&draft==LLAMA_TOKEN_NULL){draft=qwen_post_mtp_draft();mtp=draft!=LLAMA_TOKEN_NULL;if(mtp&&llama_vocab_is_eog(llama_model_get_vocab(m_),draft)){draft=LLAMA_TOKEN_NULL;mtp=false;}}
  }
  const auto before=e_.speculative_step_stats();if(!bonus_)qwen_app_routing_event_begin();bonus_=false;
  auto token=draft==LLAMA_TOKEN_NULL?e_.next():e_.next_with_one_draft(draft);
  if(draft!=LLAMA_TOKEN_NULL){const auto after=e_.speculative_step_stats();++attempts_;++causal_proposals;if(mtp)++MTP_proposals;
   if(after.attempts!=before.attempts+1||after.accepted+after.rejected!=before.accepted+before.rejected+1)throw std::runtime_error("Complete MTP target decision required");bonus_=after.accepted==before.accepted+1;}
  if(!token.end_of_generation)history_.push_back(token.id);return token;
 }
 void finish()override{e_.finish();}
 std::optional<ExpertCacheMetrics>expert_cache_metrics()const override{return e_.expert_cache_metrics();}
};
}
