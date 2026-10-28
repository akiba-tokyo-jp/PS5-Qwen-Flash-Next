// SPDX-License-Identifier: MIT
#pragma once
#include "llama.h"
#include "logit_difference.h"
#include <array>
#include <thread>
#include <vector>
#include <nlohmann/json.hpp>

namespace qwen_app {
struct ProbeStateDigest {
    std::array<unsigned char,32> metadata{},tensors{},geometry{};
    std::uint64_t metadata_bytes=0,tensor_bytes=0,readback_calls=0,tensor_sections=0;
    std::int32_t minimum=-1,maximum=-1;
};
class SpeculativeBatchProbe {
public:
    explicit SpeculativeBatchProbe(std::size_t columns);
    ~SpeculativeBatchProbe();
    void arm(bool enabled);
    bool requested()const;
    void observe(unsigned kind,llama_context *,const float *,const float *);
    void decision(bool accepted,std::int32_t committed_position,bool bonus_pinned);
    nlohmann::json report()const;
private:
    std::size_t columns_;
    std::thread::id owner_=std::this_thread::get_id();
    std::vector<float> reference_,scratch_;
    std::array<ProbeStateDigest,3> states_{};
    std::array<LogitDifference,4> comparisons_{};
    unsigned observations_=0;
    bool enabled_=false,accepted_=false,bonus_=false;
    std::int32_t committed_position_=-1;
};
bool speculative_batch_probe_requested();
void speculative_batch_probe_observe(unsigned,llama_context *,const float *,const float *);
void speculative_batch_probe_decision(bool,std::int32_t,bool);
nlohmann::json logit_difference_report(const LogitDifference &);
}
