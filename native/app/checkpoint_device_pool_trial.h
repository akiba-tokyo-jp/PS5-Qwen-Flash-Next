// SPDX-License-Identifier: MIT
#pragma once
// Vulkan F32 checkpoint pooling. Context ABI and original mode0 are unchanged.
#include <atomic>
#include <cstring>
#include <limits>
extern "C" bool qwen_checkpoint_vk_copy_batch(ggml_tensor*const*,ggml_tensor*const*,std::size_t);
namespace qwen_checkpoint_trial {
struct Counters {std::atomic<std::uint64_t>descriptor_hits{0},high_water_hits{0},batches{0},tensors{0},individual{0};};
static std::atomic<unsigned>mode{0};static Counters counters;
constexpr std::size_t bucket=2u<<20,maximum=136u<<20;
inline bool reuse_enabled(){const auto m=mode.load(std::memory_order_relaxed);return m==1||m==2;}
inline void copy(const std::vector<ggml_tensor*>&src,const std::vector<ggml_tensor*>&dst){
    GGML_ASSERT(src.size()==dst.size());const auto m=mode.load(std::memory_order_relaxed);
    if((m==2||m==3)&&!src.empty()&&qwen_checkpoint_vk_copy_batch(src.data(),dst.data(),src.size())){
        ++counters.batches;counters.tensors+=src.size();return;
    }
    for(std::size_t i=0;i<src.size();++i){ggml_backend_tensor_copy(src[i],dst[i]);++counters.individual;}
}
inline bool add(std::size_t&offset,std::size_t size,std::size_t alignment){
    if(!alignment)return false;const auto pad=(alignment-size%alignment)%alignment;
    if(size>maximum||pad>maximum-size||offset>maximum-size-pad)return false;
    offset+=size+pad;return true;
}
inline ggml_tensor probe(std::size_t bytes){
    ggml_tensor t{};t.type=GGML_TYPE_F32;t.ne[0]=int64_t(bytes/4);t.nb[0]=4;
    for(unsigned j=1;j<4;++j){t.ne[j]=1;t.nb[j]=bytes;}return t;
}
inline bool vulkan(ggml_backend_buffer_type_t buft){return std::strncmp(ggml_backend_buft_name(buft),"Vulkan",6)==0;}
template<class Writes>bool reuse_descriptors(const Writes&writes,llama_memory_buffers&buffers){
    if(!reuse_enabled()||writes.empty())return false;std::size_t matched=0;
    // Admit every buffer, source identity/range and metadata capacity before
    // resetting a descriptor arena or submitting any device copy.
    for(auto&entry:buffers){auto*buft=entry.first;auto&b=entry.second;std::size_t count=0,bytes=0;
        if(b.ctx){const auto arena=reinterpret_cast<std::uintptr_t>(ggml_get_mem_buffer(b.ctx.get()));const auto size=ggml_get_mem_size(b.ctx.get());
            for(const auto&w:writes){const auto ptr=reinterpret_cast<std::uintptr_t>(w.tensor);if(ptr>=arena&&ptr-arena<size)return false;}
        }
        const auto alignment=ggml_backend_buft_get_alignment(buft);
        if(!alignment)return false;
        std::size_t needed=b.buf?(alignment-reinterpret_cast<std::uintptr_t>(ggml_backend_buffer_get_base(b.buf.get()))%alignment)%alignment:0;
        for(const auto&w:writes){
            if(!w.tensor||!w.tensor->buffer)return false;
            if(ggml_backend_buffer_get_type(w.tensor->buffer)!=buft)continue;
            if(!vulkan(buft)||!b.buf||!b.ctx||w.tensor->buffer==b.buf.get()||w.tensor->type!=GGML_TYPE_F32||!w.size||w.offset%4||w.size%4||
               w.offset>ggml_nbytes(w.tensor)||w.size>ggml_nbytes(w.tensor)-w.offset)return false;
            if(w.size>maximum-bytes)return false;bytes+=w.size;auto t=probe(w.size);
            if(!add(needed,ggml_backend_buft_get_alloc_size(buft,&t),alignment))return false;++count;
        }
        if(!count)continue;
        if(count>512||count>b.org.capacity()||count>b.cpy.capacity()||2*count*ggml_tensor_overhead()>ggml_get_mem_size(b.ctx.get())||
           needed>ggml_backend_buffer_get_size(b.buf.get()))return false;
        matched+=count;
    }
    if(matched!=writes.size())return false;
    for(auto&entry:buffers){auto*buft=entry.first;auto&b=entry.second;std::size_t bytes=0,count=0;
        for(const auto&w:writes)if(ggml_backend_buffer_get_type(w.tensor->buffer)==buft){bytes+=w.size;++count;}
        if(!count)continue;
        const bool changed=bytes!=b.total_size;
        ggml_reset(b.ctx.get());b.org.clear();b.cpy.clear();b.total_size=bytes;b.n_tensors=count;
        auto allocator=ggml_tallocr_new(b.buf.get());
        for(const auto&w:writes)if(ggml_backend_buffer_get_type(w.tensor->buffer)==buft){
            auto*o=ggml_view_1d(b.ctx.get(),w.tensor,w.size/4,w.offset);auto*c=ggml_new_tensor_1d(b.ctx.get(),GGML_TYPE_F32,w.size/4);
            ggml_backend_view_init(o);ggml_tallocr_alloc(&allocator,c);b.org.push_back(o);b.cpy.push_back(c);
        }
        if(changed)++counters.high_water_hits;
    }
    for(auto&entry:buffers){bool present=false;for(const auto&w:writes)if(ggml_backend_buffer_get_type(w.tensor->buffer)==entry.first){present=true;break;}
        if(present)copy(entry.second.org,entry.second.cpy);
    }
    ++counters.descriptor_hits;return true;
}
inline bool fits(ggml_backend_buffer_t buffer,const std::vector<ggml_tensor*>&tensors){
    if(!reuse_enabled()||!buffer||!vulkan(ggml_backend_buffer_get_type(buffer)))return false;
    const auto alignment=ggml_backend_buft_get_alignment(ggml_backend_buffer_get_type(buffer));if(!alignment)return false;
    std::size_t needed=(alignment-reinterpret_cast<std::uintptr_t>(ggml_backend_buffer_get_base(buffer))%alignment)%alignment;
    for(auto*t:tensors)if(t->type!=GGML_TYPE_F32||!add(needed,ggml_backend_buffer_get_alloc_size(buffer,t),alignment))return false;
    if(needed>ggml_backend_buffer_get_size(buffer))return false;++counters.high_water_hits;return true;
}
template<class Buffer>ggml_backend_buffer_t allocate(Buffer&b,ggml_backend_buffer_type_t buft){
    if(!reuse_enabled()||!vulkan(buft))return ggml_backend_alloc_ctx_tensors_from_buft(b.ctx.get(),buft);
    const auto alignment=ggml_backend_buft_get_alignment(buft);if(!alignment||alignment>bucket)return ggml_backend_alloc_ctx_tensors_from_buft(b.ctx.get(),buft);
    std::size_t needed=alignment-1;
    for(auto*t:b.cpy)if(t->type!=GGML_TYPE_F32||!add(needed,ggml_backend_buft_get_alloc_size(buft,t),alignment))
        return ggml_backend_alloc_ctx_tensors_from_buft(b.ctx.get(),buft);
    const auto capacity=((needed+bucket-1)/bucket)*bucket;
    if(!capacity||capacity>maximum)return ggml_backend_alloc_ctx_tensors_from_buft(b.ctx.get(),buft);
    auto*buffer=ggml_backend_buft_alloc_buffer(buft,capacity);if(!buffer)return nullptr;
    auto allocator=ggml_tallocr_new(buffer);
    for(auto*t:b.org)ggml_backend_view_init(t);
    for(auto*t:b.cpy)ggml_tallocr_alloc(&allocator,t);
    return buffer;
}
}
extern "C" void qwen_checkpoint_trial_select(unsigned mode){
    if(mode>3)throw std::runtime_error("Unknown bounded checkpoint mode");
    qwen_checkpoint_trial::mode.store(mode,std::memory_order_release);
}
extern "C" void qwen_checkpoint_trial_stats(std::uint64_t*out){
    const auto&s=qwen_checkpoint_trial::counters;out[0]=s.descriptor_hits.load();out[1]=s.high_water_hits.load();out[2]=s.batches.load();out[3]=s.tensors.load();out[4]=s.individual.load();
}
