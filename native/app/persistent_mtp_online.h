// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include "llama.h"
#include <functional>
#include <nlohmann/json.hpp>
namespace qwen_app {
struct MtpOnlineDecision {unsigned attempts=0,accepted=0,rejected=0,queued_bonus=0;};
struct MtpOnlineHooks {
    void(*begin)()=nullptr;void(*complete)()=nullptr;void(*checkpoint)()=nullptr;void(*stage)(const char*)=nullptr;
    std::function<void()>guard;
    std::function<Token(std::int32_t)>verify;
    std::function<MtpOnlineDecision()>decision;
};
// One finite request. The original target verifier remains the only token
// authority. Persistent auxiliary KV consumes accepted drafts with the saved
// first target row before requesting another proposal.
class PersistentMtpOnline final:public Engine {
    struct State;State*state_=nullptr;
public:
    PersistentMtpOnline(Engine&,llama_model*,llama_context*,MtpOnlineHooks,unsigned maximum_attempts=6,bool force_one_wrong_draft=false);
    ~PersistentMtpOnline()override;
    std::uint32_t tokenize(const std::string&)override;
    void prefill(std::uint32_t)override;
    Token next()override;
    void finish()override;
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override;
    nlohmann::json report()const;
};
}
