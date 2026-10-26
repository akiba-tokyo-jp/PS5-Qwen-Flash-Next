// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <mutex>
#include <stdexcept>
#include <thread>
namespace qwen_app {
struct BatchIOPlan {std::uint64_t id=0,offset=0,bytes=0;};
struct BatchIOEvent {
    BatchIOPlan plan;
    std::uint64_t begin_ns=0,end_ns=0;
    std::int64_t result=0;
    bool begun=false,returned=false;
};
struct BatchIOSnapshot {
    std::array<BatchIOEvent,6> events{};
    unsigned count=0;
    bool uncertain=false;
    bool all_returned()const {
        if(!count||uncertain)return false;
        for(unsigned i=0;i<count;++i)if(!events[i].returned)return false;
        return true;
    }
    bool all_started_returned()const {
        if(uncertain)return false;
        for(unsigned i=0;i<count;++i)if(events[i].begun&&!events[i].returned)return false;
        return true;
    }
};
// The caller retains all real descriptor/bank leases. Persist the complete plan
// before admit_durable(), then persist a returned snapshot before GPU work.
// Unknown completion never permits record reuse, even after a late return.
class BatchIOJournal {
    std::thread::id producer_=std::this_thread::get_id();
    std::mutex mutex_;
    BatchIOSnapshot snapshot_{};
    bool active_=false,admitted_=false;
    void owner()const {
        if(producer_!=std::this_thread::get_id())throw std::logic_error("Batch journal requires its original producer");
    }
    BatchIOEvent &find(std::uint64_t id) {
        for(unsigned i=0;i<snapshot_.count;++i)if(snapshot_.events[i].plan.id==id)return snapshot_.events[i];
        throw std::invalid_argument("I/O event has no declared batch lease");
    }
public:
    BatchIOJournal()=default;
    BatchIOJournal(const BatchIOJournal &)=delete;
    BatchIOJournal &operator=(const BatchIOJournal &)=delete;
    void prepare(const BatchIOPlan *plans,unsigned count) {
        owner();std::lock_guard<std::mutex> lock(mutex_);
        if(active_||snapshot_.uncertain||!plans||!count||count>6)
            throw std::logic_error("A fresh completed batch journal is required");
        BatchIOSnapshot next{};next.count=count;
        for(unsigned i=0;i<count;++i) {
            const auto &p=plans[i];
            if(!p.id||!p.bytes||p.bytes>(12u<<20)||p.bytes%16384||p.offset%16384||
               p.offset>(512u<<20)||p.bytes>(512u<<20)-p.offset)
                throw std::invalid_argument("Declared I/O bytes exceed the bounded source scope");
            for(unsigned j=0;j<i;++j)if(plans[j].id==p.id)throw std::invalid_argument("Batch I/O IDs must be unique");
            next.events[i].plan=p;
        }
        snapshot_=next;active_=true;admitted_=false;
    }
    void admit_durable() {
        owner();std::lock_guard<std::mutex> lock(mutex_);
        if(!active_||admitted_||snapshot_.uncertain)throw std::logic_error("A new durable batch plan is required");
        admitted_=true;
    }
    void begin(std::uint64_t id,std::uint64_t offset,std::uint64_t bytes,std::uint64_t ns) {
        std::lock_guard<std::mutex> lock(mutex_);auto &e=find(id);
        if(!active_||!admitted_||snapshot_.uncertain||e.begun||e.returned||e.plan.offset!=offset||e.plan.bytes!=bytes||!ns)
            throw std::logic_error("I/O start disagrees with its durable owned plan");
        e.begun=true;e.begin_ns=ns;
    }
    void returned(std::uint64_t id,std::int64_t result,std::uint64_t ns) {
        std::lock_guard<std::mutex> lock(mutex_);auto &e=find(id);
        if(!active_||!admitted_||!e.begun||e.returned||ns<e.begin_ns)
            throw std::logic_error("I/O return has no matching started call");
        e.result=result;e.end_ns=ns;e.returned=true;
    }
    BatchIOSnapshot snapshot() {
        owner();std::lock_guard<std::mutex> lock(mutex_);
        if(!active_)throw std::logic_error("No active batch journal exists");
        return snapshot_;
    }
    void retain_uncertain() {
        owner();std::lock_guard<std::mutex> lock(mutex_);
        if(!active_)throw std::logic_error("No active uncertain batch exists");
        snapshot_.uncertain=true;
    }
    void finish_after_durable_return() {
        owner();std::lock_guard<std::mutex> lock(mutex_);
        if(!active_||!admitted_||!snapshot_.all_returned())throw std::logic_error("Batch completion is unknown or incomplete");
        for(unsigned i=0;i<snapshot_.count;++i)if(snapshot_.events[i].result!=std::int64_t(snapshot_.events[i].plan.bytes))
            throw std::logic_error("Batch returned an unexpected byte count");
        active_=false;admitted_=false;
    }
};
}
