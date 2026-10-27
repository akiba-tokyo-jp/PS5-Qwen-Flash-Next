// SPDX-License-Identifier: MIT
// The shipping persistent worker, exercised without a model or GPU owner.
#include "source_contention_probe_io.h"
#include "expert_prefetch_io.h"
#include "online_expert_verification.h"
#include <array>
#include <cstring>
namespace {
qwen_app::ExpertPrefetchIO *worker=nullptr;
std::array<job,3> active{};
bool submitted=false;
}
extern "C" int predictive_worker_start() {
    try{if(worker)return 0;worker=new qwen_app::ExpertPrefetchIO;return 1;}catch(...){return 0;}
}
extern "C" int predictive_worker_submit(const job *jobs) {
    try {
        if(!worker||submitted||!jobs)return 0;
        std::copy_n(jobs,3,active.begin());
        worker->submit([] {
            for(unsigned role=0;role<3;++role) {
                probe_execute_read(&active[role],role,0);
                if(active[role].sample.got!=ssize_t(active[role].bytes)||active[role].sample.error)
                    throw std::runtime_error("Native original-role read did not complete exactly; resources retained");
            }
        });
        submitted=true;return 1;
    }catch(...){return 0;}
}
extern "C" int predictive_worker_complete(job *jobs) {
    try {
        if(!worker||!submitted||!jobs)return 0;
        worker->complete();std::copy(active.begin(),active.end(),jobs);submitted=false;return 1;
    }catch(...){return 0;}
}
extern "C" int predictive_worker_stop() {
    try{if(!worker||submitted)return 0;worker->close_completed();delete worker;worker=nullptr;return 1;}catch(...){return 0;}
}
extern "C" int predictive_worker_foreground_cost_control() {
    try {
    // Metadata arithmetic control, explicitly not model quality or timing.
    qwen_app::SingleTokenExpertRoutes route{};
    for(unsigned layer=0;layer<48;++layer)for(unsigned i=0;i<10;++i)route[layer*10+i]=i;
    auto planner=std::make_unique<qwen_app::OnlineExpertVerification>();
    planner->observe(7,route,1,.95);planner->observe(8,route,1,.95);
    if(planner->choose(7,8)!=2)return 0;
    planner->verified(true,.01,0);
    if(planner->choose(7,8)!=2)return 0;
    planner->verified(false,10,10);
    return planner->choose(7,8)==1;
    }catch(...){return 0;}
}
