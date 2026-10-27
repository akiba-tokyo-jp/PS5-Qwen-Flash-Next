// SPDX-License-Identifier: MIT
#pragma once
#include "ready_source_coordinator.h"
#include <limits>
namespace qwen_app {
enum class ReadyExecutionMode { one_graph_serial,split_serial,split_overlap };
enum class ReadyGraphPhase { complete_serial,first_group,second_group,original_reduction };
struct ReadyExecutionOps {
    // The native adapter records a durable phase plan, computes the exact graph,
    // synchronizes and checks the driver before returning true. A returned
    // graph status alone is never a positive native completion proof.
    bool (*dispatch_and_complete)(ReadyGraphPhase,std::uint64_t,const std::array<bool,10>&,void *)=nullptr;
    void *opaque=nullptr;
};
struct ReadyExecutionSnapshot {
    bool attempted=false,completed=false,failed=false,owners_must_be_retained=false;
    unsigned completed_graphs=0;
    std::uint64_t last_completed_GPU_epoch=0;
};
// Construct and keep this owner inside the six real nested backing callbacks.
// On failure the caller retains this object, its source callback context,
// graphs, outputs and backing. It must not unwind a joinable coordinator.
class ReadyExpertExecution {
    const std::thread::id producer_=std::this_thread::get_id();
    ReadySourceCoordinator source_;ReadyExecutionSnapshot state_{};
    void producer()const {
        if(std::this_thread::get_id()!=producer_)throw std::logic_error("Ready execution requires the sole original GPU producer");
    }
public:
    ReadyExpertExecution()=default;
    ReadyExpertExecution(const ReadyExpertExecution&)=delete;
    ReadyExpertExecution&operator=(const ReadyExpertExecution&)=delete;
    ReadyExecutionSnapshot snapshot()const{producer();return state_;}
    ReadySourceSnapshot source_snapshot(){producer();return source_.snapshot();}
    void run(ReadyExpertWave &wave,ReadyExecutionMode mode,ReadySourceCoordinator::Fill fill,void *source_context,
             ReadyExecutionOps ops,std::uint64_t prior_completed_epoch,ReadySourceCoordinator::Deadline deadline) {
        producer();
        if(state_.attempted||!fill||!ops.dispatch_and_complete||!prior_completed_epoch||
           prior_completed_epoch>std::numeric_limits<std::uint64_t>::max()-3||
           (mode!=ReadyExecutionMode::one_graph_serial&&mode!=ReadyExecutionMode::split_serial&&mode!=ReadyExecutionMode::split_overlap))
            throw std::invalid_argument("One fresh ready-expert execution and complete native operations are required");
        state_.attempted=true;
        try {
            const auto original=wave.snapshot();
            if(original.failed||original.retired||original.IO_pending||original.GPU_pending||original.waves||
               original.reduction_complete||original.GPU_epoch||original.prior_completed_GPU_epoch!=prior_completed_epoch||!wave.may_overlap_groups())
                throw std::invalid_argument("Ready execution requires the untouched two-group owner");
            auto bounded=[&]{if(std::chrono::steady_clock::now()>=deadline)
                throw std::runtime_error("Ready execution deadline exceeded before new work; owners retained");};
            auto compute=[&](ReadyGraphPhase phase,std::uint64_t epoch,const std::array<bool,10> &selected) {
                bounded();
                if(!ops.dispatch_and_complete(phase,epoch,selected,ops.opaque))
                    throw std::runtime_error("Ready graph lacks positive synchronized driver completion; owners retained");
                ++state_.completed_graphs;state_.last_completed_GPU_epoch=epoch;
                bounded();
            };
            bounded();source_.start(wave,mode==ReadyExecutionMode::split_overlap?ReadySourceMode::overlap:ReadySourceMode::serial,fill,source_context);
            std::array<bool,10> all{};all.fill(true);
            if(mode==ReadyExecutionMode::one_graph_serial) {
                source_.join_completed(deadline);bounded();wave.begin_serial_graph(prior_completed_epoch+1);
                compute(ReadyGraphPhase::complete_serial,prior_completed_epoch+1,all);
                wave.complete_serial_graph(original.plan_epoch,prior_completed_epoch+1,true);
            } else {
                std::array<bool,10> selected{};
                if(mode==ReadyExecutionMode::split_overlap) {
                    source_.wait_first_returned(deadline);bounded();
                    selected=source_.begin_first_wave_and_release_second(prior_completed_epoch+1);
                } else {source_.join_completed(deadline);bounded();selected=wave.begin_wave(0,prior_completed_epoch+1);}
                compute(ReadyGraphPhase::first_group,prior_completed_epoch+1,selected);
                wave.complete_wave(original.plan_epoch,prior_completed_epoch+1,true);
                if(mode==ReadyExecutionMode::split_overlap)source_.join_completed(deadline);
                bounded();selected=wave.begin_wave(1,prior_completed_epoch+2);
                compute(ReadyGraphPhase::second_group,prior_completed_epoch+2,selected);
                wave.complete_wave(original.plan_epoch,prior_completed_epoch+2,true);
                bounded();wave.begin_original_reduction(prior_completed_epoch+3);
                compute(ReadyGraphPhase::original_reduction,prior_completed_epoch+3,all);
                wave.complete_original_reduction(original.plan_epoch,prior_completed_epoch+3,true);
            }
            if(!source_.snapshot().joined)throw std::logic_error("Source join is required before ready execution retirement");
            wave.retire_completed(original.plan_epoch);state_.completed=true;
        } catch(...) {state_.failed=true;state_.owners_must_be_retained=true;throw;}
    }
    // This can join only a returned callback thread; it cannot cancel I/O, free
    // backing, retry a graph or turn a failed execution into positive retirement.
    void retain_and_join_returned_source(ReadySourceCoordinator::Deadline deadline) {
        producer();if(!state_.failed)throw std::logic_error("Only a failed retained source may use this join path");
        const auto s=source_.snapshot();
        if(!s.joined)source_.retain_and_join_returned_thread(deadline);
    }
};
}
