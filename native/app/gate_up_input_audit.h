// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include <array>
#include <atomic>
#include <cstdint>
#include <nlohmann/json.hpp>

namespace qwen_app {
struct GateUpInputSnapshot {
    std::uint64_t calls=0,unsupported=0,geometry_failures=0,input_mismatches=0,ID_mismatches=0;
    std::array<std::uint64_t,5> width_calls{},layer_masks{};
};
class GateUpInputAudit {
    std::atomic<std::uint64_t> calls_{0},unsupported_{0},geometry_{0},inputs_{0},ids_{0};
    std::array<std::atomic<std::uint64_t>,5> widths_{},layers_{};
public:
    // Observe metadata only. Never retain a tensor, read its values, change the
    // graph, allocate memory, split scheduling or stop healthy inference.
    void observe(const ggml_tensor *up,const ggml_tensor *gate,int layer) noexcept {
        calls_.fetch_add(1,std::memory_order_relaxed);
        if(layer<0||layer>=48||!up||!gate||up->op!=GGML_OP_MUL_MAT_ID||gate->op!=GGML_OP_MUL_MAT_ID||
           !up->src[1]||!gate->src[1]||!up->src[2]||!gate->src[2]){
            unsupported_.fetch_add(1,std::memory_order_relaxed);return;
        }
        const auto *a=up->src[1],*b=gate->src[1],*ia=up->src[2],*ib=gate->src[2];
        const auto width=a->ne[2];
        if(a->type!=GGML_TYPE_F32||b->type!=GGML_TYPE_F32||a->ne[0]!=2560||b->ne[0]!=2560||
           a->ne[1]!=1||b->ne[1]!=1||width<=0||width>256||b->ne[2]!=width||
           ia->type!=GGML_TYPE_I32||ib->type!=GGML_TYPE_I32||ia->ne[1]!=width||ib->ne[1]!=width){
            geometry_.fetch_add(1,std::memory_order_relaxed);return;
        }
        const unsigned bucket=width==1?0:width==2?1:width==30?2:width==32?3:4;
        widths_[bucket].fetch_add(1,std::memory_order_relaxed);
        layers_[bucket].fetch_or(std::uint64_t(1)<<unsigned(layer),std::memory_order_relaxed);
        if(a!=b)inputs_.fetch_add(1,std::memory_order_relaxed);
        if(ia!=ib)ids_.fetch_add(1,std::memory_order_relaxed);
    }
    GateUpInputSnapshot snapshot()const noexcept {
        GateUpInputSnapshot out;out.calls=calls_.load();out.unsupported=unsupported_.load();
        out.geometry_failures=geometry_.load();out.input_mismatches=inputs_.load();out.ID_mismatches=ids_.load();
        for(unsigned i=0;i<5;++i){out.width_calls[i]=widths_[i].load();out.layer_masks[i]=layers_[i].load();}return out;
    }
};
nlohmann::json gate_up_input_audit_report();
}
extern "C" void qwen_observe_gate_up_inputs(const ggml_tensor*,const ggml_tensor*,int) noexcept;
