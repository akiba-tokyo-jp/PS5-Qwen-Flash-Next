// SPDX-License-Identifier: MIT
#pragma once
// Included after the pinned llama context definitions. No context ABI changes.
#include <array>
#include <atomic>
#include <limits>
#include <cstring>
extern "C" bool qwen_checkpoint_vk_copy_batch(ggml_tensor*const*,ggml_tensor*const*,std::size_t);
namespace qwen_checkpoint_trial {
struct Counters {std::atomic<std::uint64_t>descriptor_hits{0},high_water_hits{0},batches{0},tensors{0},individual{0};};
static std::atomic<unsigned>mode{0};
static Counters counters;
inline bool reuse_enabled(){const auto m=mode.load(std::memory_order_relaxed);return m==1||m==2;}
inline void copy(const std::vector<ggml_tensor*>&src,const std::vector<ggml_tensor*>&dst){
    GGML_ASSERT(src.size()==dst.size());
    const auto m=mode.load(std::memory_order_relaxed);
    if((m==2||m==3)&&!src.empty()&&qwen_checkpoint_vk_copy_batch(src.data(),dst.data(),src.size())){
        ++counters.batches;counters.tensors+=src.size();return;
    }
    for(std::size_t i=0;i<src.size();++i){ggml_backend_tensor_copy(src[i],dst[i]);++counters.individual;}
}
template<class Writes>bool reuse_descriptors(const Writes&writes,llama_memory_buffers&buffers){
    if(!reuse_enabled()||writes.empty())return false;
    std::size_t matched=0;
    for(auto&entry:buffers){auto*buft=entry.first;auto&b=entry.second;std::size_t i=0;
        for(const auto&w:writes){
            if(!w.tensor->buffer||ggml_backend_buffer_get_type(w.tensor->buffer)!=buft)continue;
            if(!b.buf||i>=b.org.size()||i>=b.cpy.size()||w.size%ggml_element_size(w.tensor))return false;
            const auto*root=w.tensor;std::size_t offset=w.offset;
            while(root->view_src){if(root->view_offs>std::numeric_limits<std::size_t>::max()-offset)return false;offset+=root->view_offs;root=root->view_src;}
            const auto*o=b.org[i];const auto*c=b.cpy[i];
            if(o->type!=w.tensor->type||c->type!=w.tensor->type||o->ne[0]!=int64_t(w.size/ggml_element_size(w.tensor))||
               o->ne[1]!=1||o->ne[2]!=1||o->ne[3]!=1||!ggml_are_same_shape(o,c)||
               o->view_src!=root||o->view_offs!=offset||o->buffer!=w.tensor->buffer||c->buffer!=b.buf.get()||
               o->data!=static_cast<const char*>(w.tensor->data)+w.offset||ggml_nbytes(o)!=w.size||
               !ggml_is_contiguous(o)||!ggml_is_contiguous(c))return false;
            ++i;++matched;
        }
        if(i&& (i!=b.org.size()||i!=b.cpy.size()||i!=b.n_tensors))return false;
    }
    if(matched!=writes.size())return false;
    // Validate every span and identity before copying any data.
    for(auto&entry:buffers){auto&b=entry.second;bool present=false;
        for(const auto&w:writes)if(ggml_backend_buffer_get_type(w.tensor->buffer)==entry.first){present=true;break;}
        if(present)copy(b.org,b.cpy);
    }
    ++counters.descriptor_hits;return true;
}
inline bool fits(ggml_backend_buffer_t buffer,const std::vector<ggml_tensor*>&tensors){
    if(!reuse_enabled()||!buffer||std::strncmp(ggml_backend_buffer_name(buffer),"Vulkan",6)!=0)return false;
    const auto capacity=ggml_backend_buffer_get_size(buffer);
    const auto alignment=ggml_backend_buft_get_alignment(ggml_backend_buffer_get_type(buffer));
    if(!alignment)return false;
    const auto base=reinterpret_cast<std::uintptr_t>(ggml_backend_buffer_get_base(buffer));
    std::size_t offset=(alignment-base%alignment)%alignment;
    for(auto*t:tensors){const auto size=ggml_backend_buffer_get_alloc_size(buffer,t);
        if(offset>capacity||size>capacity-offset)return false;
        const auto padding=(alignment-size%alignment)%alignment;
        if(size>std::numeric_limits<std::size_t>::max()-padding||size+padding>std::numeric_limits<std::size_t>::max()-offset)return false;
        offset+=size+padding;
    }
    if(offset>capacity)return false;
    ++counters.high_water_hits;return true;
}
}
extern "C" void qwen_checkpoint_trial_select(unsigned mode){
    if(mode>3)throw std::runtime_error("Unknown bounded checkpoint mode");
    // The caller changes mode only at a positively completed owner boundary.
    qwen_checkpoint_trial::mode.store(mode,std::memory_order_release);
}
extern "C" void qwen_checkpoint_trial_stats(std::uint64_t*out){
    const auto&s=qwen_checkpoint_trial::counters;
    out[0]=s.descriptor_hits.load();out[1]=s.high_water_hits.load();out[2]=s.batches.load();out[3]=s.tensors.load();out[4]=s.individual.load();
}
