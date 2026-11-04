// SPDX-License-Identifier: MIT
#pragma once
#include "session.h"
#include "llama.h"
#include <functional>
#include <nlohmann/json.hpp>

namespace qwen_app {
struct MtpShadowBoundaries {
    void(*begin)()=nullptr;void(*complete)()=nullptr;void(*checkpoint)()=nullptr;
    void(*stage)(const char*)=nullptr;std::function<void()>guard;
    // A shadow must stop if its borrowed target starts speculative width-two
    // work. Hidden-row reconciliation is qualified separately before adoption.
    std::function<bool()>target_is_ordinary;
};
// Observe ordinary target decisions. Auxiliary predictions never select,
// replace, suppress or publish an output token in this qualification scope.
class PersistentMtpShadow final:public Engine {
    struct State;State*state_=nullptr;
public:
    PersistentMtpShadow(Engine&target,llama_model*model,llama_context*context,MtpShadowBoundaries boundaries,
        bool reverse_auxiliary_order=false);
    ~PersistentMtpShadow()override;
    std::uint32_t tokenize(const std::string&)override;
    void prefill(std::uint32_t)override;
    Token next()override;
    void finish()override;
    std::optional<ExpertCacheMetrics>expert_cache_metrics()const override;
    nlohmann::json report()const;
};
}
