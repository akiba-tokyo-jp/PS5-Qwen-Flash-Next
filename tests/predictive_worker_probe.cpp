// SPDX-License-Identifier: MIT
// Test the exact native probe adapter around the shipping worker.
#include "source_contention_probe_io.h"
#include <array>
#include <iostream>
#include <stdexcept>
extern "C" int predictive_worker_start();
extern "C" int predictive_worker_submit(const job *);
extern "C" int predictive_worker_complete(job *);
extern "C" int predictive_worker_stop();
extern "C" int predictive_worker_foreground_cost_control();
static unsigned calls=0;
extern "C" void probe_execute_read(job *j,unsigned role,int noop) {
    if(noop||role>=3||j->fd!=int(role)||j->bytes!=16384)throw std::runtime_error("Native worker adapter changed a request");
    j->target[0]=static_cast<unsigned char>(role+1);j->sample.got=j->bytes;j->sample.error=0;++calls;
}
static void check(bool v){if(!v)throw std::runtime_error("Actual native worker adapter check failed");}
int main(){try {
    check(!predictive_worker_submit(nullptr));check(predictive_worker_start());check(!predictive_worker_start());
    std::array<unsigned char,3> data{};std::array<job,3> jobs{};
    for(unsigned i=0;i<3;++i){jobs[i].fd=int(i);jobs[i].target=&data[i];jobs[i].bytes=16384;}
    for(unsigned n=0;n<4;++n){check(predictive_worker_submit(jobs.data()));
        check(!predictive_worker_submit(jobs.data()));check(!predictive_worker_stop());
        check(predictive_worker_foreground_cost_control());check(predictive_worker_complete(jobs.data()));
        for(unsigned i=0;i<3;++i)check(data[i]==i+1&&jobs[i].sample.got==16384&&!jobs[i].sample.error);
        check(!predictive_worker_complete(jobs.data()));}
    check(predictive_worker_stop());check(!predictive_worker_stop());check(calls==12);
    std::cout<<"{\"actual_native_worker_adapter\":true,\"jobs\":4,\"role_reads\":12,\"passed\":true}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
