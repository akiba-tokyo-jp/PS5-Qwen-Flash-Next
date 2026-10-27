// SPDX-License-Identifier: MIT
#include "padded_cache_bridge.h"
#include "padded_bank_bridge.h"
#include "padded_bank_layout.h"
#include "padded_bank.h"
#include "padded_cache_geometry.h"
#include "mapped_source_bridge.h"
#include <atomic>
#include <stdexcept>
namespace {std::atomic<bool> enabled{false};std::atomic<std::size_t> descriptor_alignment{0};
struct ReadLease {const void *first,*second;unsigned count;const int *slots;std::size_t residue;};
int read_bank(void *target,std::size_t capacity,std::uint64_t flags,std::size_t alignment,void *opaque){
    const auto &read=*static_cast<const ReadLease *>(opaque);
    if((flags&7)!=7||alignment!=descriptor_alignment.load())
        throw std::runtime_error("Padded cache mapping flags or descriptor alignment changed");
    return qwen_app_read_owned_bank(read.first,read.second,read.count,read.slots,
        read.residue,target,capacity,alignment)?0:1;
}}
namespace qwen_app {
void configure_native_padded_cache(bool value,std::size_t alignment){
    if(value&&!qwen_app_model_compute_limits_enabled())
        throw std::runtime_error("Padded cache requires the admitted native device ledger");
    configure_padded_index_layout(value,alignment);
    descriptor_alignment.store(value?alignment:0);enabled.store(value);
}
}
extern "C" bool qwen_app_padded_cache_enabled(){return enabled.load();}
extern "C" std::size_t qwen_app_padded_buffer_batch_limit(std::size_t actual){
    return qwen_app::selected_padded_buffer_batch_limit(actual,qwen_app_model_compute_limits_enabled());
}
extern "C" bool qwen_app_try_owned_bank_reads(ggml_tensor *bank,const void *first,const void *second,
    unsigned count,const int *slots,std::size_t residue){
    if(!enabled.load()||!slots||!first||(count!=1&&count!=2)||(count==2&&!second))
        throw std::invalid_argument("Padded cache requires the exact owned read request");
    ReadLease read{first,second,count,slots,residue};
    // The backend retains the actual shared vk_buffer through every synchronous
    // read return. An exception deliberately prevents normal resource retirement.
    return ggml_app_vk_probe_owned_bank(bank,read_bank,&read)==0;
}
