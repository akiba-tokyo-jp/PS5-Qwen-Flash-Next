// SPDX-License-Identifier: MIT
#include "ready_expert_wave.h"
#include <atomic>
#include <future>
#include <iostream>
#include <memory>
using namespace qwen_app;
namespace {
constexpr std::array<std::int32_t,10> experts{{0,1,2,3,4,5,6,7,8,9}};
constexpr std::array<unsigned,10> slots{{0,26,1,27,2,28,3,29,4,30}};
constexpr ReadyExpertWave::Owners distinct{{{{11,11,11}},{{22,22,22}}}};
constexpr ReadyExpertWave::Owners aliases{{{{11,11,11}},{{11,11,11}}}};
unsigned refusals=0,retentions=0;
void check(bool value){if(!value)throw std::runtime_error("Ready-wave metadata invariant failed");}
template<class F> void refuse(F run){bool caught=false;try{run();}catch(...){caught=true;}check(caught);++refusals;}
ReadyExpertWave plan(ReadyExpertWave::Owners owners=distinct){return ReadyExpertWave(experts,slots,owners,47,1,17,1);}
void resident_group(ReadyExpertWave &p,unsigned group) {
    for(unsigned i=0;i<10;++i)if(unsigned(slots[i]>=26)==group)p.admit_resident(slots[i],47*512+experts[i],1);
}
void fill_group(ReadyExpertWave &p,unsigned group,std::uint64_t &operation) {
    for(unsigned i=0;i<10;++i)if(unsigned(slots[i]>=26)==group)
        for(unsigned role=0;role<3;++role){p.begin_role_read(slots[i],role,++operation);p.complete_role_read(17,operation,bank_expert_bytes,true,true);}
}
void finish(ReadyExpertWave &p) {
    const auto order=p.begin_original_reduction(4);for(unsigned i=0;i<10;++i)check(order[i]==i);
    const std::array<float,10> values{{16777216.0f,1.0f,-16777216.0f,1.0f,0,0,0,0,0,0}};
    float original=0,actual=0,first=0,second=0;
    for(unsigned i=0;i<10;++i){original+=values[i];actual+=values[order[i]];(slots[i]<26?first:second)+=values[i];}
    check(original==1.0f&&actual==original&&first+second==2.0f);
    refuse([&]{p.retire_completed(17);});p.complete_original_reduction(17,4,true);
    refuse([&]{p.retire_completed(16);});p.retire_completed(17);check(p.snapshot().retired);
    refuse([&]{p.begin_wave(0,5);});
}
}
int main() {
    {
        auto p=plan();p.bind_reader(std::this_thread::get_id());check(p.may_overlap_groups()&&p.snapshot().ready_experts==0);
        refuse([&]{p.begin_wave(0,2);});refuse([&]{p.begin_original_reduction(2);});refuse([&]{p.retire_completed(17);});
        std::uint64_t op=0;fill_group(p,0,op);
        p.begin_role_read(26,0,++op);auto mask=p.begin_wave(0,2);
        check(p.snapshot().IO_pending&&p.snapshot().GPU_pending);
        for(unsigned i=0;i<10;++i)check(mask[i]==(slots[i]<26));
        p.complete_role_read(17,op,bank_expert_bytes,true,true);
        for(unsigned i=1;i<10;i+=2)for(unsigned role=i==1?1:0;role<3;++role){p.begin_role_read(slots[i],role,++op);p.complete_role_read(17,op,bank_expert_bytes,true,true);}
        refuse([&]{p.begin_wave(1,3);});refuse([&]{p.begin_role_read(0,0,++op);});
        p.complete_wave(17,2,true);p.begin_wave(1,3);p.complete_wave(17,3,true);
        check(p.snapshot().role_reads==30&&p.snapshot().role_returns==30&&p.snapshot().ready_experts==10);finish(p);
    }
    {
        auto p=plan();p.bind_reader(std::this_thread::get_id());resident_group(p,0);resident_group(p,1);
        p.begin_wave(0,2);p.complete_wave(17,2,true);p.begin_wave(1,3);p.complete_wave(17,3,true);
        check(p.snapshot().role_reads==0);finish(p);
    }
    {
        auto p=plan();p.bind_reader(std::this_thread::get_id());resident_group(p,0);std::uint64_t op=0;
        p.begin_wave(0,2);fill_group(p,1,op);check(p.snapshot().GPU_pending&&p.snapshot().role_returns==15);
        p.complete_wave(17,2,true);p.begin_wave(1,3);p.complete_wave(17,3,true);finish(p);
    }
    {
        auto p=plan();p.bind_reader(std::this_thread::get_id());resident_group(p,1);std::uint64_t op=0;
        refuse([&]{p.begin_role_read_pair(0,0,0,1);});refuse([&]{p.begin_role_read_pair(0,26,0,1);});
        p.begin_role_read_pair(0,1,0,++op);p.begin_wave(1,2);
        check(p.snapshot().IO_pending&&p.snapshot().GPU_pending&&p.snapshot().role_reads==2);
        refuse([&]{p.begin_role_read(2,0,2);});p.complete_role_read(17,op,2*bank_expert_bytes,true,true);
        for(unsigned role=0;role<3;++role) {
            if(role){p.begin_role_read_pair(0,1,role,++op);p.complete_role_read(17,op,2*bank_expert_bytes,true,true);}
            p.begin_role_read_pair(2,3,role,++op);p.complete_role_read(17,op,2*bank_expert_bytes,true,true);
            p.begin_role_read(4,role,++op);p.complete_role_read(17,op,bank_expert_bytes,true,true);
        }
        check(p.snapshot().role_reads==15&&p.snapshot().role_returns==15&&p.snapshot().read_leases==9);
        p.complete_wave(17,2,true);p.begin_wave(0,3);p.complete_wave(17,3,true);finish(p);
    }
    for(bool reversed:{false,true}) {
        auto p=plan(aliases);p.bind_reader(std::this_thread::get_id());resident_group(p,0);check(!p.may_overlap_groups());
        if(reversed){p.begin_role_read(26,0,1);refuse([&]{p.begin_wave(0,2);});p.complete_role_read(17,1,bank_expert_bytes,true,true);}
        p.begin_wave(0,2);refuse([&]{p.begin_role_read(26,reversed?1:0,2);});
        check(!p.snapshot().failed&&p.snapshot().GPU_pending);p.complete_wave(17,2,true);
        p.begin_role_read(26,reversed?1:0,3);p.complete_role_read(17,3,bank_expert_bytes,true,true);
    }
    {
        std::array<std::int32_t,10> repeated{{4,8,4,8,4,8,4,8,4,8}};
        std::array<unsigned,10> repeated_slots{{0,52,0,52,0,52,0,52,0,52}};
        ReadyExpertWave p(repeated,repeated_slots,distinct,0,1,17,1);p.bind_reader(std::this_thread::get_id());
        p.admit_resident(0,4,1);p.admit_resident(52,8,1);check(p.snapshot().unique_experts==2);
        p.begin_wave(0,2);p.complete_wave(17,2,true);p.begin_wave(1,3);p.complete_wave(17,3,true);
        const auto order=p.begin_original_reduction(4);for(unsigned i=0;i<10;++i)check(order[i]==i&&p.snapshot().contributions[i]);
        p.complete_original_reduction(17,4,true);p.retire_completed(17);
    }
    for(unsigned bad=0;bad<5;++bad) {
        auto p=plan();p.bind_reader(std::this_thread::get_id());p.begin_role_read(0,0,1);
        refuse([&]{p.complete_role_read(bad==3?16:17,bad==4?2:1,bad==0?bank_expert_bytes-1:bank_expert_bytes,bad!=1,bad!=2);});
        const auto state=p.snapshot();check(state.failed&&state.IO_pending&&state.role_returns==0&&state.ready_experts==0);
        check(state.IO_call_returned==(bad==0||bad==2));refuse([&]{p.begin_role_read(1,0,3);});refuse([&]{p.retire_completed(17);});++retentions;
    }
    {
        auto p=plan();p.bind_reader(std::this_thread::get_id());p.begin_role_read_pair(0,1,0,1);
        refuse([&]{p.complete_role_read(17,1,bank_expert_bytes,true,true);});
        const auto state=p.snapshot();check(state.failed&&state.IO_pending&&state.IO_call_returned&&state.role_reads==2&&state.role_returns==0&&state.ready_experts==0);++retentions;
    }
    for(bool stale:{false,true}) {
        auto p=plan();p.bind_reader(std::this_thread::get_id());resident_group(p,0);resident_group(p,1);p.begin_wave(0,2);
        refuse([&]{p.complete_wave(stale?16:17,2,stale);});check(p.snapshot().failed&&p.snapshot().GPU_pending);
        refuse([&]{p.begin_wave(1,3);});refuse([&]{p.retire_completed(17);});++retentions;
    }
    for(bool stale:{false,true}) {
        auto p=plan();p.bind_reader(std::this_thread::get_id());resident_group(p,0);resident_group(p,1);
        p.begin_wave(0,2);p.complete_wave(17,2,true);p.begin_wave(1,3);p.complete_wave(17,3,true);p.begin_original_reduction(4);
        refuse([&]{p.complete_original_reduction(stale?16:17,4,stale);});check(p.snapshot().failed&&p.snapshot().GPU_pending&&!p.snapshot().retired);++retentions;
    }
    {
        auto p=plan();p.bind_reader(std::this_thread::get_id());
        refuse([&]{p.admit_resident(0,0,1);});refuse([&]{p.admit_resident(0,47*512,2);});
        refuse([&]{p.bind_reader(std::this_thread::get_id());});refuse([&]{p.begin_role_read(53,0,1);});refuse([&]{p.begin_role_read(0,3,1);});
        std::atomic<unsigned> refused{0};std::thread other([&]{try{p.begin_wave(0,2);}catch(...){++refused;}try{p.begin_role_read(0,0,1);}catch(...){++refused;}});other.join();check(refused==2&&!p.snapshot().failed);
    }
    {
        auto p=plan();resident_group(p,0);std::promise<void> launch,start,returned;
        auto allowed=launch.get_future();auto done=returned.get_future();
        std::exception_ptr error;
        std::thread worker([&]{allowed.wait();bool announced=false;try{p.begin_role_read(26,0,1);start.set_value();announced=true;done.wait();p.complete_role_read(17,1,bank_expert_bytes,true,true);}catch(...){error=std::current_exception();if(!announced)start.set_exception(error);}});
        p.bind_reader(worker.get_id());p.begin_wave(0,2);launch.set_value();
        auto started=start.get_future();const auto status=started.wait_for(std::chrono::seconds(3));
        if(status==std::future_status::ready){try{started.get();}catch(...){returned.set_value();worker.join();throw;}}
        else {returned.set_value();worker.join();throw std::runtime_error("Bounded host reader signal missing");}
        check(p.snapshot().IO_pending&&p.snapshot().GPU_pending);returned.set_value();worker.join();if(error)std::rethrow_exception(error);
        p.complete_wave(17,2,true);check(!p.snapshot().IO_pending&&!p.snapshot().GPU_pending&&p.snapshot().role_returns==1);
    }
    {
        constexpr std::array<unsigned,10> same_group{{0,1,2,3,4,5,6,7,8,9}};
        ReadyExpertWave p(experts,same_group,distinct,47,1,17,1);p.bind_reader(std::this_thread::get_id());
        check(!p.may_overlap_groups());for(unsigned i=0;i<10;++i)p.admit_resident(i,47*512+experts[i],1);
        refuse([&]{p.begin_wave(1,2);});p.begin_wave(0,2);p.complete_wave(17,2,true);
        const auto order=p.begin_original_reduction(3);for(unsigned i=0;i<10;++i)check(order[i]==i);
        p.complete_original_reduction(17,3,true);p.retire_completed(17);check(p.snapshot().waves==1);
    }
    refuse([&]{auto bad=experts;bad[0]=-1;ReadyExpertWave p(bad,slots,distinct,0,1,17,1);});
    refuse([&]{auto bad=slots;bad[0]=53;ReadyExpertWave p(experts,bad,distinct,0,1,17,1);});
    refuse([&]{auto bad=slots;bad[1]=bad[0];ReadyExpertWave p(experts,bad,distinct,0,1,17,1);});
    refuse([&]{auto bad=experts;bad[1]=bad[0];ReadyExpertWave p(bad,slots,distinct,0,1,17,1);});
    refuse([&]{auto bad=distinct;bad[0][0]=0;ReadyExpertWave p(experts,slots,bad,0,1,17,1);});
    refuse([&]{ReadyExpertWave p(experts,slots,distinct,48,1,17,1);});
    refuse([&]{ReadyExpertWave p(experts,slots,distinct,0,0,17,1);});
    refuse([&]{ReadyExpertWave p(experts,slots,distinct,0,1,0,1);});
    refuse([&]{ReadyExpertWave p(experts,slots,distinct,0,1,17,0);});
    refuse([&]{auto p=plan();p.bind_reader({});});
    refuse([&]{auto p=plan();p.bind_reader(std::this_thread::get_id());p.begin_role_read(52,0,1);});
    std::cout<<"{\"metadata_refusals\":"<<refusals<<",\"unknown_or_failed_retention_cases\":"<<retentions
        <<",\"actual_host_reader_thread_checked\":true,\"original_reduction_order_checked\":true,\"metadata_bytes\":"<<sizeof(ReadyExpertWave)
        <<",\"actual_GPU_or_IO_overlap_measured\":false,\"PS5_operations\":0}"<<std::endl;
}
