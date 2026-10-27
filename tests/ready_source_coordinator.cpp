// SPDX-License-Identifier: MIT
// Actual scheduler, role owner and two-call I/O controller; metadata callbacks
// return byte counts without dereferencing the fake addresses or reading files.
#include "ready_source_coordinator.h"
#include "vectored_source_batch.h"
#include <atomic>
#include <iostream>
#include <string>
using namespace qwen_app;
static void check(bool good){if(!good)throw std::runtime_error("Ready coordinator control failed");}
static auto deadline(){return std::chrono::steady_clock::now()+std::chrono::seconds(3);}
struct Source {
    ReadyExpertWave *wave=nullptr;std::string scenario;
    std::mutex mutex;std::condition_variable changed;unsigned pending=0,peak=0,pair_entered=0,pair_left=0;
    bool pair=false;std::uint64_t operation=0,id=0;unsigned reads=0,fills=0,overlap_calls=0;
    std::array<bool,2> stage_entered{};bool stage_released=false;
    static std::int64_t read(void *opaque,const VectoredRead &r) {
        auto &s=*static_cast<Source *>(opaque);std::unique_lock<std::mutex> lock(s.mutex);++s.pending;++s.reads;s.peak=std::max(s.peak,s.pending);
        if(s.wave->snapshot().GPU_pending)++s.overlap_calls;
        if(s.pair) {
            ++s.pair_entered;s.changed.notify_all();
            check(s.changed.wait_until(lock,deadline(),[&]{return s.pair_entered==2;}));
            ++s.pair_left;
        }
        --s.pending;return r.bytes();
    }
    static void fill(ReadyExpertWave &wave,unsigned group,void *opaque) {
        auto &s=*static_cast<Source *>(opaque);++s.fills;
        if((s.scenario=="first-exception"&&!group)||(s.scenario=="second-exception"&&group))throw std::runtime_error("Known callback exception");
        if(s.scenario=="missing-role"&&!group)return;
        if((!group&&(s.scenario=="first-deadline"||s.scenario=="early-release"))||(group&&s.scenario=="second-deadline")) {
            std::unique_lock<std::mutex> lock(s.mutex);s.stage_entered[group]=true;s.changed.notify_all();
            check(s.changed.wait_until(lock,deadline(),[&]{return s.stage_released;}));
        }
        VectoredSourceBatch reader(read,&s);reader.start();
        for(unsigned role=0;role<3;++role)for(unsigned i=0;i<5;i+=2) {
            const unsigned count=i==4?1:2;const auto first=group?48+i:i;
            if(count==2)wave.begin_role_read_pair(first,first+1,role,++s.operation);
            else wave.begin_role_read(first,role,++s.operation);
            std::array<VectoredRead,2> requests{};
            for(unsigned j=0;j<count;++j) {
                auto &r=requests[j];r.fd=7;r.device=1;r.inode=2;r.file_bytes=512u<<20;r.id=++s.id;r.count=1;
                r.offset=(4u<<20)+(group*5+i+j)*padded_bank_stride;
                const auto local=group?22+i+j:i+j;
                r.destinations[0]={reinterpret_cast<void *>((group?0x20000000000ull:0x10000000000ull)+role*(128ull<<20)+local*padded_bank_stride),std::uint32_t(padded_bank_stride)};
            }
            {std::lock_guard<std::mutex> lock(s.mutex);s.pair=count==2;s.pair_entered=s.pair_left=0;}
            reader.read(requests.data(),count);
            wave.complete_role_read(17,s.operation,count*bank_expert_bytes,true,true);
        }
        reader.stop_completed();
    }
};
#ifndef QWEN_READY_SOURCE_NO_MAIN
int main(int argc,char **argv) {
    check(argc==2);const std::string scenario=argv[1];
    std::array<std::int32_t,10> experts{};std::array<unsigned,10> slots{};
    for(unsigned i=0;i<10;++i){experts[i]=i;slots[i]=i<5?i:48+i-5;}
    ReadyExpertWave::Owners owners{{{{11,11,11}},{{22,22,22}}}};
    if(scenario=="aliased-groups")owners[1][0]=11;
    ReadyExpertWave wave(experts,slots,owners,47,1,17,1);Source source;source.wave=&wave;source.scenario=scenario;
    ReadySourceCoordinator coordinator;unsigned refusals=0;
    const auto refuse=[&](auto operation){try{operation();}catch(const std::exception &){++refusals;return;}throw std::runtime_error("Expected coordinator refusal missing");};
    const auto finish_wave=[&](unsigned group,unsigned epoch){(void)wave.begin_wave(group,epoch);wave.complete_wave(17,epoch,true);};
    const auto wait_stage=[&](unsigned group){std::unique_lock<std::mutex> lock(source.mutex);check(source.changed.wait_until(lock,deadline(),[&]{return source.stage_entered[group];}));};
    const auto release_stage=[&]{std::lock_guard<std::mutex> lock(source.mutex);source.stage_released=true;source.changed.notify_all();};
    const bool serial=scenario=="serial";
    if(scenario=="before-start") {
        refuse([&]{coordinator.wait_first_returned(deadline());});refuse([&]{coordinator.join_completed(deadline());});
        refuse([&]{coordinator.begin_first_wave_and_release_second(2);});
    }else if(scenario=="null-callback"||scenario=="aliased-groups"||scenario=="invalid-mode") {
        refuse([&]{coordinator.start(wave,scenario=="invalid-mode"?static_cast<ReadySourceMode>(9):ReadySourceMode::overlap,
            scenario=="null-callback"?nullptr:Source::fill,&source);});check(!source.fills);
    }else {
        if(scenario=="already-bound")wave.bind_reader(std::this_thread::get_id());
        if(scenario=="wrong-active-wave")for(unsigned i=5;i<10;++i)wave.admit_resident(slots[i],47*512+experts[i],1);
        if(scenario=="already-bound") {
            refuse([&]{coordinator.start(wave,ReadySourceMode::overlap,Source::fill,&source);});check(coordinator.snapshot().joined&&!source.fills);
        }else {
            coordinator.start(wave,serial?ReadySourceMode::serial:ReadySourceMode::overlap,Source::fill,&source);
            if(scenario=="wrong-thread") {
                std::thread other([&]{refuse([&]{coordinator.wait_first_returned(deadline());});});other.join();
            }
            if(scenario=="first-deadline") {
                wait_stage(0);refuse([&]{coordinator.wait_first_returned(std::chrono::steady_clock::now()-std::chrono::seconds(1));});
                release_stage();coordinator.retain_and_join_returned_thread(deadline());
                check(source.fills==1&&coordinator.snapshot().failed);
            }else if(scenario=="first-exception") {
                refuse([&]{coordinator.wait_first_returned(deadline());});coordinator.retain_and_join_returned_thread(deadline());
                check(source.fills==1&&coordinator.snapshot().failed);
            }else {
                if(scenario=="early-release") {
                    wait_stage(0);refuse([&]{coordinator.begin_first_wave_and_release_second(2);});release_stage();
                }
                coordinator.wait_first_returned(deadline());
                if(scenario=="wrong-active-wave") {
                    (void)wave.begin_wave(1,2);refuse([&]{coordinator.begin_first_wave_and_release_second(3);});
                    coordinator.retain_and_join_returned_thread(deadline());check(source.fills==1&&wave.snapshot().GPU_pending);
                }else if(scenario=="missing-role") {
                    refuse([&]{coordinator.begin_first_wave_and_release_second(2);});coordinator.retain_and_join_returned_thread(deadline());check(source.fills==1);
                }else if(scenario=="cancel-before-second") {
                    coordinator.retain_and_join_returned_thread(deadline());check(source.fills==1&&source.reads==15);
                }else {
                    if(serial) {
                        coordinator.join_completed(deadline());check(source.overlap_calls==0);finish_wave(0,2);
                    }else {
                        if(scenario=="repeat-start")refuse([&]{coordinator.start(wave,ReadySourceMode::overlap,Source::fill,&source);});
                        const auto selection=coordinator.begin_first_wave_and_release_second(2);for(unsigned i=0;i<10;++i)check(selection[i]==(i<5));
                        if(scenario=="repeat-release")refuse([&]{coordinator.begin_first_wave_and_release_second(2);});
                        if(scenario=="second-deadline") {
                            wait_stage(1);refuse([&]{coordinator.join_completed(std::chrono::steady_clock::now()-std::chrono::seconds(1));});
                            release_stage();coordinator.retain_and_join_returned_thread(deadline());
                            check(coordinator.snapshot().failed&&wave.snapshot().GPU_pending);
                        }else if(scenario=="second-exception") {
                            refuse([&]{coordinator.join_completed(deadline());});coordinator.retain_and_join_returned_thread(deadline());
                        }else {
                            // Hold the metadata GPU lease until all actual
                            // two-call controllers return. No GPU arithmetic.
                            coordinator.join_completed(deadline());check(source.overlap_calls==15);wave.complete_wave(17,2,true);
                        }
                    }
                    if(scenario!="second-exception"&&scenario!="second-deadline") {
                        finish_wave(1,3);const auto order=wave.begin_original_reduction(4);
                        for(unsigned i=0;i<10;++i)check(order[i]==i);
                        wave.complete_original_reduction(17,4,true);wave.retire_completed(17);
                        check(wave.snapshot().retired&&source.reads==30&&source.peak==2&&source.fills==2);
                        if(scenario=="repeat-join")refuse([&]{coordinator.join_completed(deadline());});
                    }
                }
            }
            check(coordinator.snapshot().joined);
        }
    }
    std::cout<<"{\"passed\":true,\"refusals\":"<<refusals<<",\"metadata_read_callbacks\":"<<source.reads
        <<",\"peak_two_call_depth\":"<<source.peak<<",\"callbacks_during_GPU_lease\":"<<source.overlap_calls
        <<",\"PS5_operations\":0,\"file_reads\":0,\"GPU_calls\":0}\n";
}
#endif
