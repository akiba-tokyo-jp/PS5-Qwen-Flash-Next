// SPDX-License-Identifier: MIT
// Exercise the real coordinator/role owner/two-call controller. Read and graph
// callbacks handle metadata only: no weights, arithmetic, files or GPU commands.
#define QWEN_READY_SOURCE_NO_MAIN
#include "ready_source_coordinator.cpp"
#include "ready_expert_execution.h"
struct Graphs {
    ReadyExpertWave *wave=nullptr;Source *source=nullptr;
    ReadyExecutionMode mode=ReadyExecutionMode::split_overlap;
    std::string scenario;unsigned calls=0;
    static bool complete(ReadyGraphPhase phase,std::uint64_t epoch,const std::array<bool,10> &selected,void *opaque) {
        auto &g=*static_cast<Graphs *>(opaque);const auto before=g.wave->snapshot();
        check(before.GPU_pending&&before.GPU_epoch==epoch);
        if(g.mode!=ReadyExecutionMode::split_overlap||phase!=ReadyGraphPhase::first_group)check(!before.IO_pending);
        const unsigned at=g.calls++;
        for(unsigned i=0;i<10;++i)check(selected[i]==(phase==ReadyGraphPhase::complete_serial||phase==ReadyGraphPhase::original_reduction||
            (phase==ReadyGraphPhase::first_group?i<5:i>=5)));
        if(g.mode==ReadyExecutionMode::one_graph_serial)check(phase==ReadyGraphPhase::complete_serial&&at==0&&before.ready_experts==10);
        else check(phase==(at==0?ReadyGraphPhase::first_group:at==1?ReadyGraphPhase::second_group:ReadyGraphPhase::original_reduction));
        if(g.mode==ReadyExecutionMode::split_overlap&&at==0&&g.scenario!="second-exception") {
            // Keep the metadata lease until the actual two-call controller
            // returns group one. This tests scheduling, not a GPU speed gain.
            const auto until=deadline();
            while(g.wave->snapshot().role_returns!=30) {
                check(std::chrono::steady_clock::now()<until);std::this_thread::yield();
            }
        }
        if(g.scenario=="false-"+std::to_string(at))return false;
        if(g.scenario=="throw-"+std::to_string(at))throw std::runtime_error("Returned graph callback exception");
        return true;
    }
};
int main(int argc,char **argv) {try {
    check(argc==2);const std::string scenario=argv[1];
    std::array<std::int32_t,10> experts{};std::array<unsigned,10> slots{};
    for(unsigned i=0;i<10;++i){experts[i]=i;slots[i]=i<5?i:48+i-5;}
    ReadyExpertWave::Owners owners{{{{11,11,11}},{{22,22,22}}}};
    ReadyExpertWave wave(experts,slots,owners,47,1,17,1);
    Source source;source.wave=&wave;source.scenario=scenario;
    auto mode=scenario=="one-graph"?ReadyExecutionMode::one_graph_serial:
        scenario=="split-serial"?ReadyExecutionMode::split_serial:ReadyExecutionMode::split_overlap;
    Graphs graphs;graphs.wave=&wave;graphs.source=&source;graphs.mode=mode;graphs.scenario=scenario;
    ReadyExpertExecution execution;unsigned refused=0;
    const auto refuse=[&](auto op){try{op();}catch(const std::exception &){++refused;return;}throw std::runtime_error("Expected ready execution refusal missing");};
    auto run=[&](auto selected,std::uint64_t prior,auto until){execution.run(wave,selected,Source::fill,&source,{Graphs::complete,&graphs},prior,until);};
    if(scenario=="serial-partial-ready"||scenario=="serial-stale-completion"||scenario=="serial-wrong-completion") {
        wave.bind_reader(std::this_thread::get_id());
        for(unsigned i=0;i<5;++i)wave.admit_resident(slots[i],47*512+experts[i],1);
        if(scenario=="serial-partial-ready") {refuse([&]{wave.begin_serial_graph(2);});check(!wave.snapshot().GPU_pending);}
        else {
            for(unsigned i=5;i<10;++i)wave.admit_resident(slots[i],47*512+experts[i],1);
            wave.begin_serial_graph(2);
            if(scenario=="serial-stale-completion")refuse([&]{wave.complete_serial_graph(16,2,true);});
            else refuse([&]{wave.complete_wave(17,2,true);});
            check(wave.snapshot().failed&&wave.snapshot().GPU_pending&&!wave.snapshot().reduction_complete);
        }
    }else if(scenario=="wrong-thread") {
        std::thread other([&]{refuse([&]{run(mode,1,deadline());});});other.join();check(!execution.snapshot().attempted);
    }else if(scenario=="invalid-mode"||scenario=="wrong-prior"||scenario=="expired") {
        refuse([&]{run(scenario=="invalid-mode"?static_cast<ReadyExecutionMode>(9):mode,
            scenario=="wrong-prior"?2:1,scenario=="expired"?std::chrono::steady_clock::now()-std::chrono::seconds(1):deadline());});
        check(!source.fills&&!graphs.calls);
    }else {
        const bool failing=scenario.rfind("false-",0)==0||scenario.rfind("throw-",0)==0||
            scenario=="first-exception"||scenario=="second-exception"||scenario=="missing-role";
        if(failing) {
            refuse([&]{run(mode,1,deadline());});check(execution.snapshot().failed&&execution.snapshot().owners_must_be_retained&&!execution.snapshot().completed);
            execution.retain_and_join_returned_source(deadline());check(execution.source_snapshot().joined);
            refuse([&]{run(mode,1,deadline());});check(!wave.snapshot().retired);
        }else {
            run(mode,1,deadline());const auto e=execution.snapshot();
            check(e.completed&&!e.failed&&!e.owners_must_be_retained&&wave.snapshot().retired&&execution.source_snapshot().joined);
            check(e.completed_graphs==(mode==ReadyExecutionMode::one_graph_serial?1u:3u));
            check(source.reads==30&&source.peak==2&&wave.snapshot().role_returns==30);
            check(source.overlap_calls==(mode==ReadyExecutionMode::split_overlap?15u:0u));
            if(scenario=="repeat")refuse([&]{run(mode,1,deadline());});
        }
    }
    std::cout<<"{\"passed\":true,\"refusals\":"<<refused<<",\"graph_completion_callbacks\":"<<graphs.calls
        <<",\"metadata_read_callbacks\":"<<source.reads<<",\"peak_two_call_depth\":"<<source.peak
        <<",\"callbacks_during_GPU_lease\":"<<source.overlap_calls<<",\"PS5_operations\":0,\"GPU_calls\":0,\"file_reads\":0}\n";
    return 0;
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
