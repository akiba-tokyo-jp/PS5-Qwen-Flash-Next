// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <stdexcept>
#include <thread>
namespace qwen_app {
// One context, one completed prefix, and its final consumer only. The pinned
// ON_DEVICE writer releases its old buffer before allocating a changed-size
// replacement. The allocator's real aggregate cap is independently unchanged.
class FinalPrefixHandoff {
    const void *engine_=nullptr,*context_=nullptr;
    std::thread::id producer_=std::this_thread::get_id();
    bool certified_=false,armed_=false,consumed_=false;
public:
    static constexpr std::uint64_t prefix_bytes=119881728,speculative_bytes=120311808;
    static std::uint64_t rounded(std::uint64_t n){return(n+(2ull<<20)-1)&~((2ull<<20)-1);}
    void certify(const void *engine,const void *context,std::uint64_t payload,bool reset){
        if(producer_!=std::this_thread::get_id()||certified_||!engine||!context||payload!=prefix_bytes||!reset)
            throw std::runtime_error("One complete positively reset original prefix required");
        engine_=engine;context_=context;certified_=true;
    }
    void arm(const void *engine,const void *context,unsigned ordinal,bool restored){
        if(producer_!=std::this_thread::get_id()||!certified_||armed_||consumed_||engine!=engine_||context!=context_||ordinal!=2||!restored)
            throw std::runtime_error("Only the final completed prefix consumer may hand off its snapshot");
        armed_=true;
    }
    bool pending(const void *engine,const void *context)const{
        return armed_&&!consumed_&&engine==engine_&&context==context_&&producer_==std::this_thread::get_id();
    }
    void consume(const void *engine,const void *context,std::uint64_t payload,std::int32_t position){
        if(!pending(engine,context)||payload!=prefix_bytes||position!=30)
            throw std::runtime_error("Prefix handoff source owner, payload or committed position differs");
        consumed_=true;
    }
    std::uint64_t new_allocation(const void *context,std::uint64_t bytes)const{
        if(!consumed_)return rounded(bytes);
        if(context!=context_||bytes!=speculative_bytes||rounded(prefix_bytes)!=rounded(bytes)||producer_!=std::this_thread::get_id())
            throw std::runtime_error("Only the exact same-capacity final snapshot replacement is qualified");
        return 0;
    }
    bool consumed()const{return consumed_;}
};
inline FinalPrefixHandoff final_prefix_handoff;
}
