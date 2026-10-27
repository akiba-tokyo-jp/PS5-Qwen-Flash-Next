// SPDX-License-Identifier: MIT
#include "split_bank_allocation.h"
#include "native_gpu.h"
#include "system_memory.h"
#include "padded_cache_geometry.h"
#include "ggml-alloc.h"
#include "ggml-vulkan.h"
namespace qwen_app {
void SplitBankAllocation::producer()const {
    if(std::this_thread::get_id()!=producer_)throw std::logic_error("Split allocations require the original GPU producer");
}
void SplitBankAllocation::prepare(ggml_backend_t backend) {
    producer();
    if(attempted_||!backend||!ggml_backend_is_vk(backend)||selected_padded_cache_geometry().active_slots!=53)
        throw std::invalid_argument("One original 53-slot Vulkan split allocation attempt required");
    attempted_=true;backend_=backend;
    try {
        const auto type=ggml_backend_get_default_buffer_type(backend);
        if(!type)throw std::runtime_error("Split allocation requires its actual Vulkan buffer type");
        // Price every root with the actual upstream planner before requesting
        // either GPU allocation. Working/context buffers belong elsewhere.
        for(unsigned group=0;group<2;++group) {
            (void)admit_native_system_memory();
            contexts_[group]=ggml_init({ggml_tensor_overhead()*8+4096,nullptr,true});
            if(!contexts_[group])throw std::runtime_error("Split group metadata refused");
            create_split_bank_roots(contexts_[group],roots_[group]);
            charged_+=split_bank_group_charge(ggml_backend_alloc_ctx_tensors_from_buft_size(contexts_[group],type));
        }
        if(charged_>(512u<<20))throw std::length_error("Split groups exceed the retained cache allowance");
        for(unsigned group=0;group<2;++group) {
            (void)admit_native_system_memory();qwen_native_driver_checkpoint();
            buffers_[group]=ggml_backend_alloc_ctx_tensors(contexts_[group],backend);
            if(!buffers_[group]||split_bank_group_charge(ggml_backend_buffer_get_size(buffers_[group]))>split_group_buffer_cap)
                throw std::runtime_error("Split group actual buffer allocation refused");
            ggml_backend_synchronize(backend);qwen_native_driver_checkpoint();
        }
        prepared_=true;
    }catch(...){failed_=true;qwen_native_driver_retain();throw;}
}
int SplitBankAllocation::take_lease(const SplitBankLease &bank,void *opaque) {
    auto &c=*static_cast<LeaseCursor *>(opaque);
    c.owner->backings_[c.index/3][c.index%3]=bank;
    return c.owner->lease(c.index+1,c.use,c.opaque);
}
int SplitBankAllocation::lease(unsigned index,Use use,void *opaque) {
    if(index==6){(void)validate_split_bank_backings(backings_);return use(backings_,roots_,opaque);}
    LeaseCursor cursor{this,index,use,opaque};
    return ggml_app_vk_probe_owned_split_bank(roots_[index/3][index%3],index/3,take_lease,&cursor);
}
void SplitBankAllocation::with_owned_backings(Use use,void *opaque) {
    producer();
    if(!prepared_||!use||active_||completed_||failed_||closed_)
        throw std::invalid_argument("Split backing use requires one healthy synchronous owner");
    active_=true;
    try {
        // All six bridge callbacks remain on the stack throughout this use.
        // The callback must join its reads/workers and return after GPU idle;
        // escaping pointers or uncertain work are never a successful return.
        if(lease(0,use,opaque)!=0)throw std::runtime_error("Independent split backing was not eligible");
        ggml_backend_synchronize(backend_);qwen_native_driver_checkpoint();
        active_=false;completed_=true;
    }catch(...){failed_=true;qwen_native_driver_retain();throw;}
}
void SplitBankAllocation::close_completed() {
    producer();
    if(!completed_||active_||failed_||closed_)throw std::invalid_argument("Incomplete split backing cannot be retired");
    try {
        ggml_backend_synchronize(backend_);qwen_native_driver_checkpoint();
        for(unsigned reverse=2;reverse;--reverse) {
            const auto group=reverse-1;ggml_backend_buffer_free(buffers_[group]);buffers_[group]=nullptr;
            ggml_free(contexts_[group]);contexts_[group]=nullptr;qwen_native_driver_checkpoint();
        }
        closed_=true;
    }catch(...){failed_=true;qwen_native_driver_retain();throw;}
}
}
