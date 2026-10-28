// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <stdexcept>
#include <thread>
namespace qwen_app {
// Experimental accounting for the pinned one-context ON_DEVICE state writer.
// Its changed-size init releases the old buffer before allocating its replacement.
// The real allocator still checks every allocation. No live, unknown or pending
// snapshot receives credit; each capture must positively synchronize first.
class SnapshotReplacementBudget {
    const void*context_=nullptr;
    std::thread::id producer_{};
    std::uint64_t completed_=0,pending_=0,replacements_=0;
public:
    static std::uint64_t rounded(std::uint64_t n){
        if(n<118038528||n>142606336)throw std::invalid_argument("Complete original snapshot payload required");
        return(n+(2ull<<20)-1)&~((2ull<<20)-1);
    }
    void bind(const void*context){
        if(!context||context_)throw std::invalid_argument("Snapshot replacement has exactly one original context");
        context_=context;producer_=std::this_thread::get_id();
    }
    std::uint64_t begin(const void*context,std::uint64_t bytes,std::uint64_t live,std::uint64_t cap){
        if(!context_||context!=context_||producer_!=std::this_thread::get_id()||pending_||!cap||live>cap)
            throw std::runtime_error("A fresh producer-bound completed snapshot owner is required");
        const auto next=rounded(bytes),previous=completed_?rounded(completed_):0;
        if(previous>live)throw std::runtime_error("Previously certified snapshot cannot exceed actual live device ownership");
        const auto extra=next>previous?next-previous:0;
        if(extra>cap-live)throw std::runtime_error("Snapshot replacement cannot retain the unchanged device cap");
        pending_=bytes;return extra;
    }
    void completed(const void*context,std::uint64_t bytes,bool positive_GPU_checkpoint){
        if(context!=context_||producer_!=std::this_thread::get_id()||!pending_||pending_!=bytes||!positive_GPU_checkpoint)
            throw std::runtime_error("Exact pending snapshot and positive GPU copy completion required");
        if(completed_)++replacements_;completed_=bytes;pending_=0;
    }
    std::uint64_t payload()const{return completed_;}
    std::uint64_t replacements()const{return replacements_;}
    bool pending()const{return pending_!=0;}
};
}
