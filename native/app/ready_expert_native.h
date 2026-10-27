// SPDX-License-Identifier: MIT
#pragma once
#include "ready_expert_execution.h"
#include "ready_expert_graph.h"
#include "ggml-backend.h"
namespace qwen_app {
// The context, graphs, backend and six strong bank borrowers must all outlive a
// failed/unknown run. This adapter allocates graph metadata only, not weights.
class ReadyExpertNativeGraphs {
    const std::thread::id producer_=std::this_thread::get_id();
    ggml_context *context_=nullptr;
    ggml_backend_t backend_=nullptr;
    ggml_backend_buffer_t workspace_=nullptr;
    std::array<ggml_cgraph *,4> graphs_{};
    std::array<std::array<bool,10>,4> selected_{};
    bool prepared_=false,failed_=false,complete_control_=false,closed_=false;
    unsigned next_=0;
    std::uint64_t last_epoch_=0;
    void (*stage_)(const char *)=nullptr;
    void (*checkpoint_)()=nullptr;
    void producer()const;
public:
    ReadyExpertNativeGraphs()=default;
    ReadyExpertNativeGraphs(const ReadyExpertNativeGraphs&)=delete;
    ReadyExpertNativeGraphs&operator=(const ReadyExpertNativeGraphs&)=delete;
    void prepare(ggml_context *,ggml_backend_t,const std::array<ReadyExpertGraphInputs,2>&,
        ggml_tensor *output,std::uint64_t prior_completed_epoch,void (*stage)(const char *),void (*checkpoint)());
    // Price the actual planner before one bounded device allocation. Preserve
    // operational/Flexible/Direct reserves and the enabled device ledger.
    void allocate_workspace();
    ggml_cgraph *graph(ReadyGraphPhase)const;
    ReadyExecutionOps operations();
    void close_completed(ReadyExpertExecution &,const ReadyExpertWave &);
    static bool dispatch(ReadyGraphPhase,std::uint64_t,const std::array<bool,10>&,void *);
};
}
