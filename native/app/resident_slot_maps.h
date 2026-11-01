// SPDX-License-Identifier: MIT
#pragma once
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-alloc.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>
namespace qwen_app {
inline std::atomic<bool> reuse_slot_maps{false};
// Attempts, uploads, reuses, bindings, uploaded bytes, saved bytes, allocations, bytes.
inline std::array<std::uint64_t,8> slot_map_counts{};
class ResidentSlotMaps {
    static constexpr std::size_t experts=512,guard=64,stride=experts+2*guard;
    static constexpr std::int32_t sentinel=0x13579bdf;
    ggml_backend_t backend_;
    std::size_t capacity_;
    ggml_context *ctx_=nullptr;
    ggml_backend_buffer_t buffer_=nullptr;
    ggml_tensor *storage_=nullptr;
    std::vector<ggml_tensor*> maps_;
    std::vector<std::array<std::int32_t,experts>> sent_;
    std::vector<bool> valid_;
public:
    ResidentSlotMaps(ggml_backend_t backend,std::size_t layers,std::size_t capacity):
        backend_(backend),capacity_(capacity),maps_(layers),sent_(layers),valid_(layers,false) {
        if(!backend||!layers||layers>64||!capacity||capacity>INT32_MAX)
            throw std::runtime_error("Bounded resident slot-map geometry required");
        ggml_init_params params{};params.no_alloc=true;
        params.mem_size=(layers+1)*ggml_tensor_overhead()+256;
        ctx_=ggml_init(params);if(!ctx_)throw std::runtime_error("Slot-map metadata unavailable");
        storage_=ggml_new_tensor_1d(ctx_,GGML_TYPE_I32,layers*stride);
        ggml_set_input(storage_);ggml_set_output(storage_);
        // Only the owning NONE tensor is an input; GGML views retain their VIEW op.
        for(std::size_t i=0;i<layers;++i)maps_[i]=ggml_view_1d(ctx_,storage_,experts,(i*stride+guard)*sizeof(std::int32_t));
        buffer_=ggml_backend_alloc_ctx_tensors(ctx_,backend_);
        if(!buffer_){ggml_free(ctx_);ctx_=nullptr;throw std::runtime_error("Resident slot-map device buffer unavailable");}
        std::vector<std::int32_t> initial(layers*stride,sentinel);
        for(std::size_t i=0;i<layers;++i)std::fill_n(initial.begin()+i*stride+guard,experts,-1);
        ggml_backend_tensor_set(storage_,initial.data(),0,initial.size()*sizeof(std::int32_t));
        ++slot_map_counts[6];slot_map_counts[7]+=ggml_backend_buffer_get_size(buffer_);
    }
    ResidentSlotMaps(const ResidentSlotMaps&)=delete;
    ResidentSlotMaps&operator=(const ResidentSlotMaps&)=delete;
    ~ResidentSlotMaps(){if(buffer_)ggml_backend_buffer_free(buffer_);if(ctx_)ggml_free(ctx_);}
    bool publish(ggml_backend_t backend,unsigned layer,const ggml_tensor *source,ggml_tensor *destination){
        ++slot_map_counts[0];
        if(backend!=backend_||layer>=maps_.size()||!source||!destination||!source->data||
           source->type!=GGML_TYPE_I32||destination->type!=GGML_TYPE_I32||
           ggml_nbytes(source)!=experts*sizeof(std::int32_t)||ggml_nbytes(destination)!=ggml_nbytes(source)||
           !ggml_is_contiguous(source)||!ggml_is_contiguous(destination)||destination->view_src||destination->view_offs)
            return false;
        const auto *values=static_cast<const std::int32_t*>(source->data);
        for(std::size_t i=0;i<experts;++i)if(values[i]<-1||(values[i]>=0&&std::size_t(values[i])>=capacity_))
            throw std::runtime_error("Resident slot map contains an unowned Expert slot");
        const bool same=valid_[layer]&&!std::memcmp(values,sent_[layer].data(),experts*sizeof(std::int32_t));
        if(!reuse_slot_maps.load(std::memory_order_relaxed)||!same){
            // This uses the same ordered backend transfer as the original cache.
            // The original ID download/synchronization precedes every publication.
            ggml_backend_tensor_set_async(backend_,maps_[layer],values,0,experts*sizeof(std::int32_t));
            std::memcpy(sent_[layer].data(),values,experts*sizeof(std::int32_t));valid_[layer]=true;
            ++slot_map_counts[1];slot_map_counts[4]+=experts*sizeof(std::int32_t);
        }else{++slot_map_counts[2];slot_map_counts[5]+=experts*sizeof(std::int32_t);}
        // Storage is dedicated to this cache, as are its existing Expert banks.
        // Both comparison arms bind it; only byte-identical upload reuse differs.
        destination->buffer=maps_[layer]->buffer;destination->data=maps_[layer]->data;
        ++slot_map_counts[3];return true;
    }
    void verify_completed(){
        // Caller must establish successful backend completion first.
        std::vector<std::int32_t> actual(maps_.size()*stride);
        ggml_backend_tensor_get(storage_,actual.data(),0,actual.size()*sizeof(std::int32_t));
        for(std::size_t l=0;l<maps_.size();++l){
            for(std::size_t i=0;i<guard;++i)if(actual[l*stride+i]!=sentinel||actual[l*stride+guard+experts+i]!=sentinel)
                throw std::runtime_error("Resident slot-map guard differs");
            for(std::size_t i=0;i<experts;++i)if(actual[l*stride+guard+i]!=(valid_[l]?sent_[l][i]:-1))
                throw std::runtime_error("Resident GPU slot map differs from its authoritative CPU table");
        }
    }
};
}
