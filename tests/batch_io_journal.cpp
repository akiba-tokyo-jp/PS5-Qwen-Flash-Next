// SPDX-License-Identifier: MIT
#include "batch_io_journal.h"
#include <atomic>
#include <functional>
#include <iostream>
using namespace qwen_app;
void require(bool ok){if(!ok)throw std::runtime_error("Batch I/O journal control failed");}
int main() {
    unsigned refused=0;
    auto bad=[&](const std::function<void()> &f){try{f();}catch(...){++refused;return;}throw std::runtime_error("Invalid journal operation was accepted");};
    const BatchIOPlan pair[]={{1,4194304,3293184},{2,14073856,3293184}};
    BatchIOJournal journal;journal.prepare(pair,2);
    bad([&]{journal.begin(1,pair[0].offset,pair[0].bytes,10);});
    journal.admit_durable();
    bad([&]{journal.prepare(pair,2);});bad([&]{journal.admit_durable();});
    bad([&]{journal.begin(3,0,16384,10);});
    bad([&]{journal.begin(1,pair[0].offset+16384,pair[0].bytes,10);});
    bad([&]{journal.begin(1,pair[0].offset,pair[0].bytes+16384,10);});
    std::atomic<bool> foreign_refused{false};
    std::thread worker([&]{try{journal.snapshot();}catch(...){foreign_refused=true;}
        journal.begin(2,pair[1].offset,pair[1].bytes,11);journal.returned(2,pair[1].bytes,21);});
    journal.begin(1,pair[0].offset,pair[0].bytes,10);journal.returned(1,pair[0].bytes,20);worker.join();
    require(foreign_refused);auto s=journal.snapshot();require(s.all_returned()&&s.all_started_returned());
    require(s.events[0].result==3293184&&s.events[1].begin_ns==11);
    bad([&]{journal.begin(1,pair[0].offset,pair[0].bytes,30);});bad([&]{journal.returned(1,pair[0].bytes,30);});
    journal.finish_after_durable_return();journal.prepare(pair,2);journal.admit_durable();
    journal.begin(1,pair[0].offset,pair[0].bytes,30);journal.returned(1,-1,31);
    s=journal.snapshot();require(s.all_started_returned()&&!s.all_returned());
    bad([&]{journal.finish_after_durable_return();});
    journal.begin(2,pair[1].offset,pair[1].bytes,32);journal.returned(2,pair[1].bytes-16384,33);
    require(journal.snapshot().all_returned());bad([&]{journal.finish_after_durable_return();});
    BatchIOJournal unknown;unknown.prepare(pair,2);unknown.admit_durable();unknown.begin(1,pair[0].offset,pair[0].bytes,40);
    unknown.retain_uncertain();unknown.returned(1,pair[0].bytes,41);
    require(!unknown.snapshot().all_started_returned());bad([&]{unknown.finish_after_durable_return();});bad([&]{unknown.prepare(pair,2);});
    for(unsigned variant=0;variant<6;++variant) {
        BatchIOJournal fresh;auto p=pair[0];
        if(variant==0)p.id=0;if(variant==1)p.offset=1;if(variant==2)p.bytes=1;
        if(variant==3)p.bytes=13u<<20;if(variant==4)p.offset=512u<<20;if(variant==5)p.bytes=0;
        bad([&]{fresh.prepare(&p,1);});
    }
    BatchIOJournal six;std::array<BatchIOPlan,6> plans{};
    for(unsigned i=0;i<6;++i)plans[i]={i+1,4194304+i*3293184ull,3293184};
    six.prepare(plans.data(),6);six.admit_durable();
    for(unsigned wave=0;wave<3;++wave) {
        const auto a=plans[wave*2],b=plans[wave*2+1];
        std::thread lane([&]{six.begin(b.id,b.offset,b.bytes,100);six.returned(b.id,b.bytes,200);});
        six.begin(a.id,a.offset,a.bytes,100);six.returned(a.id,a.bytes,200);lane.join();
    }
    require(six.snapshot().all_returned());six.finish_after_durable_return();
    std::cout<<"{\"exact_event_records\":8,\"invalid_operations_refused\":"<<refused
        <<",\"foreign_producer_refused\":true,\"short_read_is_known_but_not_success\":true,\"uncertain_completion_retains_plan\":true,\"GPU_calls\":0}"<<std::endl;
}
