// SPDX-License-Identifier: MIT
#pragma once
#include "split_padded_bank.h"
#include <array>
#include <mutex>
#include <thread>
namespace qwen_app {
struct ReadyWaveSnapshot {
    bool failed=false,retired=false,IO_pending=false,IO_call_returned=false,GPU_pending=false,reduction_complete=false;
    unsigned unique_experts=0,ready_experts=0,role_reads=0,role_returns=0,read_leases=0,waves=0;
    std::uint64_t IO_operation=0,GPU_epoch=0;
    std::uint64_t request_epoch=0,plan_epoch=0;
    unsigned layer=0;
    std::array<bool,10> contributions{};
};
// Metadata-only prototype. It never reads, allocates, submits, retries or frees
// actual backing. The native caller must supply qualified backing-owner IDs
// and retain the graph/state after any failed or unknown completion.
class ReadyExpertWave {
public:
    using Roles=std::array<std::uint64_t,3>;
    using Owners=std::array<Roles,2>;
private:
    struct Entry {std::int32_t expert=-1;unsigned slot=0,group=0,roles=0;};
    mutable std::mutex mutex_;
    const std::thread::id producer_=std::this_thread::get_id();
    std::thread::id reader_{};
    const std::uint64_t request_epoch_,plan_epoch_,base_GPU_epoch_;
    const unsigned layer_;
    Owners owners_;
    std::array<Entry,10> entries_{};
    std::array<unsigned,10> original_{};
    unsigned count_=0;
    std::array<bool,2> group_done_{};
    ReadyWaveSnapshot state_;
    bool started_=false,reader_bound_=false,reduction_pending_=false;
    std::array<unsigned,2> IO_entries_{};
    unsigned IO_count_=0,IO_role_=0,GPU_group_=0;
    std::uint64_t last_IO_=0,last_GPU_=0;
    void producer()const {
        if(std::this_thread::get_id()!=producer_)throw std::logic_error("Ready-wave GPU producer changed");
    }
    void healthy()const {
        if(state_.failed||state_.retired)throw std::runtime_error("Ready-wave owner is quarantined or retired");
    }
    bool overlap(unsigned first,unsigned second)const {
        for(auto a:owners_[first])for(auto b:owners_[second])if(a==b)return true;
        return false;
    }
    unsigned entry(unsigned slot)const {
        for(unsigned i=0;i<count_;++i)if(entries_[i].slot==slot)return i;
        throw std::invalid_argument("Slot does not belong to this immutable original selection");
    }
    bool ready(unsigned group)const {
        bool found=false;
        for(unsigned i=0;i<count_;++i)if(entries_[i].group==group){found=true;if(entries_[i].roles!=7)return false;}
        return found&&!group_done_[group];
    }
    [[noreturn]] void quarantine(const char *message) {
        state_.failed=true;throw std::runtime_error(message);
    }
    void start_read(const std::array<unsigned,2>&slots,unsigned count,unsigned role,std::uint64_t operation) {
        std::lock_guard<std::mutex> lock(mutex_);healthy();
        if(!reader_bound_||std::this_thread::get_id()!=reader_)throw std::logic_error("Only the bound source-lease producer may fill an expert");
        if((count!=1&&count!=2)||role>=3||!operation||operation<=last_IO_||state_.IO_pending)
            throw std::invalid_argument("Ready-wave source lease/order refused before reading");
        std::array<unsigned,2> indices{};
        for(unsigned i=0;i<count;++i) {
            indices[i]=entry(slots[i]);const auto &e=entries_[indices[i]];
            if(group_done_[e.group]||(e.roles&(1u<<role))||(i&&(indices[0]==indices[1]||entries_[indices[0]].group!=e.group)))
                throw std::invalid_argument("A source pair must fill distinct unfinished roles in one owned bank group");
            if(state_.GPU_pending&&(reduction_pending_||overlap(e.group,GPU_group_)))
                throw std::invalid_argument("CPU fill cannot touch backing pinned by the GPU");
        }
        started_=true;IO_entries_=indices;IO_count_=count;IO_role_=role;last_IO_=operation;
        state_.IO_pending=true;state_.IO_call_returned=false;state_.IO_operation=operation;
        state_.role_reads+=count;++state_.read_leases;
    }
public:
    ReadyExpertWave(const std::array<std::int32_t,10>&experts,const std::array<unsigned,10>&slots,
                    Owners owners,unsigned layer,std::uint64_t request_epoch,std::uint64_t plan_epoch,std::uint64_t prior_GPU_completed_epoch):
        request_epoch_(request_epoch),plan_epoch_(plan_epoch),base_GPU_epoch_(prior_GPU_completed_epoch),layer_(layer),
        owners_(owners),last_GPU_(prior_GPU_completed_epoch) {
        if(!request_epoch_||!plan_epoch_||!base_GPU_epoch_||layer_>=48)throw std::invalid_argument("Original layer/request/plan and prior completed GPU epoch required");
        for(const auto &group:owners_)for(auto owner:group)if(!owner)throw std::invalid_argument("Actual backing-owner identities required");
        for(unsigned i=0;i<10;++i) {
            if(experts[i]<0||experts[i]>=512||slots[i]>=53)throw std::invalid_argument("Original top-k expert and global slot bounds required");
            unsigned found=count_;
            for(unsigned j=0;j<count_;++j) {
                if(entries_[j].expert==experts[i]) {
                    if(entries_[j].slot!=slots[i])throw std::invalid_argument("Repeated expert must keep one immutable slot");
                    found=j;
                }else if(entries_[j].slot==slots[i])throw std::invalid_argument("Different selected experts cannot share one slot");
            }
            if(found==count_){entries_[count_++]={experts[i],slots[i],unsigned(slots[i]>=26),0};}
            original_[i]=found;
        }
        for(unsigned group=0;group<2;++group) {
            bool found=false;for(unsigned i=0;i<count_;++i)found|=entries_[i].group==group;
            group_done_[group]=!found;
        }
        state_.unique_experts=count_;
        state_.request_epoch=request_epoch_;state_.plan_epoch=plan_epoch_;state_.layer=layer_;
    }
    void bind_reader(std::thread::id reader) {
        std::lock_guard<std::mutex> lock(mutex_);producer();healthy();
        if(started_||reader_bound_||reader==std::thread::id{})throw std::invalid_argument("Exactly one original CPU reader must be bound before work");
        reader_=reader;reader_bound_=true;
    }
    void admit_resident(unsigned slot,std::int32_t original_key,std::uint64_t completed_epoch) {
        std::lock_guard<std::mutex> lock(mutex_);producer();healthy();
        if(started_||completed_epoch!=base_GPU_epoch_)throw std::invalid_argument("Resident data requires the original prior completed epoch");
        auto &e=entries_[entry(slot)];
        if(e.roles||original_key!=std::int32_t(layer_*512)+e.expert)throw std::invalid_argument("Resident expert key or single-use admission differs");
        e.roles=7;
    }
    void begin_role_read(unsigned slot,unsigned role,std::uint64_t operation) {
        start_read({{slot,0}},1,role,operation);
    }
    void begin_role_read_pair(unsigned first,unsigned second,unsigned role,std::uint64_t operation) {
        start_read({{first,second}},2,role,operation);
    }
    void complete_role_read(std::uint64_t plan_epoch,std::uint64_t operation,std::size_t original_payload_bytes,bool all_calls_returned,bool identity_exact) {
        std::lock_guard<std::mutex> lock(mutex_);healthy();
        if(!reader_bound_||std::this_thread::get_id()!=reader_)throw std::logic_error("Ready-wave read completion producer changed");
        if(plan_epoch!=plan_epoch_||!state_.IO_pending||operation!=state_.IO_operation)quarantine("Stale source completion retains its ready-wave owner");
        state_.IO_call_returned=all_calls_returned;
        if(!all_calls_returned||!identity_exact||original_payload_bytes!=IO_count_*bank_expert_bytes)
            quarantine("Incomplete original expert role retains its source and graph backing");
        for(unsigned i=0;i<IO_count_;++i)entries_[IO_entries_[i]].roles|=1u<<IO_role_;
        state_.IO_pending=false;state_.role_returns+=IO_count_;
    }
    std::array<bool,10> begin_wave(unsigned group,std::uint64_t epoch) {
        std::lock_guard<std::mutex> lock(mutex_);producer();healthy();
        if(group>=2||!reader_bound_||state_.GPU_pending||epoch<=last_GPU_||!ready(group)||
           (state_.IO_pending&&overlap(group,entries_[IO_entries_[0]].group)))
            throw std::invalid_argument("Whole-expert readiness or independent backing is missing before GPU work");
        started_=true;GPU_group_=group;state_.GPU_pending=true;state_.GPU_epoch=epoch;reduction_pending_=false;
        std::array<bool,10> selected{};for(unsigned i=0;i<10;++i)selected[i]=entries_[original_[i]].group==group;
        return selected;
    }
    void complete_wave(std::uint64_t plan_epoch,std::uint64_t epoch,bool positive_completion) {
        std::lock_guard<std::mutex> lock(mutex_);producer();healthy();
        if(plan_epoch!=plan_epoch_||!state_.GPU_pending||reduction_pending_||epoch!=state_.GPU_epoch||!positive_completion)
            quarantine("Unknown ready-wave GPU completion retains every contribution and bank");
        for(unsigned i=0;i<10;++i)if(entries_[original_[i]].group==GPU_group_)state_.contributions[i]=true;
        group_done_[GPU_group_]=true;last_GPU_=epoch;state_.GPU_pending=false;++state_.waves;
    }
    std::array<unsigned,10> begin_original_reduction(std::uint64_t epoch) {
        std::lock_guard<std::mutex> lock(mutex_);producer();healthy();
        if(state_.IO_pending||state_.GPU_pending||state_.reduction_complete||!group_done_[0]||!group_done_[1]||epoch<=last_GPU_)
            throw std::invalid_argument("Original reduction requires every returned read and completed contribution");
        std::array<unsigned,10> order{};
        for(unsigned i=0;i<10;++i){if(!state_.contributions[i])throw std::logic_error("Original contribution is missing");order[i]=i;}
        state_.GPU_pending=true;state_.GPU_epoch=epoch;reduction_pending_=true;return order;
    }
    void complete_original_reduction(std::uint64_t plan_epoch,std::uint64_t epoch,bool positive_completion) {
        std::lock_guard<std::mutex> lock(mutex_);producer();healthy();
        if(plan_epoch!=plan_epoch_||!state_.GPU_pending||!reduction_pending_||epoch!=state_.GPU_epoch||!positive_completion)
            quarantine("Original reduction completion is unknown; backing retained");
        last_GPU_=epoch;state_.GPU_pending=false;reduction_pending_=false;state_.reduction_complete=true;
    }
    void retire_completed(std::uint64_t verified_source_completion_epoch) {
        std::lock_guard<std::mutex> lock(mutex_);producer();healthy();
        // A matching returned worker epoch permits a persistent idle reader;
        // final native teardown still separately requires its actual join.
        if(verified_source_completion_epoch!=plan_epoch_||state_.IO_pending||state_.GPU_pending||!state_.reduction_complete)
            throw std::invalid_argument("Ready-wave retirement requires positive source/GPU/consumer completion");
        state_.retired=true;
    }
    ReadyWaveSnapshot snapshot()const {
        std::lock_guard<std::mutex> lock(mutex_);auto result=state_;result.ready_experts=0;
        for(unsigned i=0;i<count_;++i)result.ready_experts+=entries_[i].roles==7;return result;
    }
    bool may_overlap_groups()const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::array<bool,2> selected{};for(unsigned i=0;i<count_;++i)selected[entries_[i].group]=true;
        return selected[0]&&selected[1]&&!overlap(0,1);
    }
};
}
