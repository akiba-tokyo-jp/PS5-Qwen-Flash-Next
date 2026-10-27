// SPDX-License-Identifier: MIT
#pragma once
#include "split_bank_bridge.h"
#include "ready_expert_wave.h"
#include "ggml-backend.h"
#include <limits>
namespace qwen_app {
using SplitBankRoots=std::array<std::array<ggml_tensor *,3>,2>;
using SplitBankBackings=std::array<std::array<SplitBankLease,3>,2>;
inline constexpr std::size_t split_group_buffer_cap=256u<<20;
inline std::size_t split_bank_group_charge(std::size_t planned) {
    constexpr std::size_t quantum=2u<<20;
    if(!planned||planned>split_group_buffer_cap)throw std::length_error("Split group exceeds its independent 256 MiB buffer allowance");
    return (planned+quantum-1)&~(quantum-1);
}
// Three roots in one context share one actual buffer. Two contexts establish
// independent groups without rounding six independent BOs up to 516 MiB.
inline void create_split_bank_roots(ggml_context *ctx,std::array<ggml_tensor *,3>&roots) {
    if(!ctx)throw std::invalid_argument("A split group requires owned tensor metadata");
    for(auto &root:roots){root=ggml_new_tensor_1d(ctx,GGML_TYPE_BF16,split_bank_planes[0]*padded_bank_stride/2);
        if(!root)throw std::runtime_error("Split root metadata allocation failed");ggml_set_input(root);}
}
inline ReadyExpertWave::Owners validate_split_bank_backings(const SplitBankBackings &banks) {
    ReadyExpertWave::Owners owners{};
    std::array<std::pair<std::uintptr_t,std::uintptr_t>,6> spans{};
    unsigned index=0;
    for(unsigned group=0;group<2;++group)for(unsigned role=0;role<3;++role) {
        const auto &b=banks[group][role];const auto address=reinterpret_cast<std::uintptr_t>(b.destination);
        if(!address||address%bank_read_alignment||b.bytes!=split_bank_planes[group]*padded_bank_stride||
           !b.allocation_owner||(b.memory_flags&7)!=7||!b.descriptor_alignment||
           b.descriptor_alignment>bank_read_alignment||(b.descriptor_alignment&(b.descriptor_alignment-1))||
           address>std::numeric_limits<std::uintptr_t>::max()-b.bytes)
            throw std::invalid_argument("Actual aligned/coherent split-bank ownership is incomplete");
        if(role&&(b.allocation_owner!=banks[group][0].allocation_owner||
            address!=reinterpret_cast<std::uintptr_t>(banks[group][role-1].destination)+banks[group][role-1].bytes))
            throw std::invalid_argument("A split group must retain three contiguous roots in one actual allocation");
        if(group&&b.allocation_owner==banks[0][0].allocation_owner)
            throw std::invalid_argument("Ready-wave groups cannot share actual VkDeviceMemory");
        const auto end=address+b.bytes;
        for(unsigned i=0;i<index;++i)if(address<spans[i].second&&spans[i].first<end)
            throw std::invalid_argument("Split CPU backing spans overlap");
        spans[index++]={address,end};owners[group][role]=b.allocation_owner;
    }
    return owners;
}
// Experimental explicit lifetime. Destruction never releases buffers: callers
// must obtain a synchronous returned use and invoke close_completed(). Failed
// or uncertain work retains raw owners for ordinary OS context teardown.
class SplitBankAllocation {
public:
    using Use=int (*)(const SplitBankBackings &,const SplitBankRoots &,void *);
    SplitBankAllocation()=default;
    SplitBankAllocation(const SplitBankAllocation&)=delete;
    SplitBankAllocation&operator=(const SplitBankAllocation&)=delete;
    void prepare(ggml_backend_t);
    void with_owned_backings(Use,void *);
    void close_completed();
    std::size_t charged_bytes()const{return charged_;}
private:
    struct LeaseCursor {SplitBankAllocation *owner;unsigned index;Use use;void *opaque;};
    static int take_lease(const SplitBankLease &,void *);
    int lease(unsigned,Use,void *);
    void producer()const;
    std::thread::id producer_=std::this_thread::get_id();
    ggml_backend_t backend_=nullptr;
    std::array<ggml_context *,2> contexts_{};
    std::array<ggml_backend_buffer_t,2> buffers_{};
    SplitBankRoots roots_{};SplitBankBackings backings_{};
    bool attempted_=false,prepared_=false,active_=false,completed_=false,closed_=false,failed_=false;
    std::size_t charged_=0;
};
}
