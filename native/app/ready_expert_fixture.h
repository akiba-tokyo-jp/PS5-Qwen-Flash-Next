// SPDX-License-Identifier: MIT
#pragma once
#include "split_bank_allocation.h"
#include <nlohmann/json.hpp>
namespace qwen_app {
struct ReadyOriginalPlan;
struct ReadyFixtureMatrix {
    std::uint64_t offset;unsigned residue;const char *raw,*envelope;
};
// A numerical repeated-ID gate, not a ten-unique-expert performance workload.
// Invoke only after the twelve independent-backing matrix graphs pass and
// inside all six synchronous strong-bank callbacks. Failed owners stay alive.
nlohmann::json run_ready_expert_fixture(ggml_backend_t,int source_fd,
    const SplitBankBackings &,const SplitBankRoots &,const std::array<ReadyFixtureMatrix,6>&,
    std::uint64_t prior_positive_graph_epoch);
nlohmann::json run_ready_original_fixture(ggml_backend_t,int source_fd,const SplitBankBackings &,
    const SplitBankRoots &,const std::array<ReadyFixtureMatrix,6>&,const ReadyOriginalPlan &,std::uint64_t prior_positive_graph_epoch);
inline void require_ready_fixture_policy(const nlohmann::json &p) {
    const auto &r=p.at("native_ready_expert_numerical");
    if(r!=nlohmann::json{{"schema","ps5-qwen-ready-numerical-policy-v1"},{"enabled",true},
        {"unique_original_experts",2u},{"original_contributions",10u},{"cohort_runs",6u},
        {"source_IO_depth",1u},{"representative_speed_test",false}})
        throw std::invalid_argument("Exact repeated-ID numerical ready-expert scope required");
    for(const auto *key:{"unique_original_experts","original_contributions","cohort_runs","source_IO_depth"})
        if(!r.at(key).is_number_unsigned())throw std::invalid_argument("Ready numerical counts require exact unsigned integers");
}
}
