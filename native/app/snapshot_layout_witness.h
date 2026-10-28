// SPDX-License-Identifier: MIT
#pragma once
#include "llama-io.h"
#include "ggml-backend.h"
#include <cstdint>
#include <stdexcept>
namespace qwen_app {
// Metadata-only traversal of the actual state writer inputs. It submits no
// download or allocation. All saved tensor slices must share one original GPU
// buffer type, preserve F32, and require no backend or per-tensor size padding.
class SnapshotLayoutWitness final:public llama_io_write_i {
    ggml_backend_buffer_type_t expected_;
    std::size_t alignment_=0;
    std::uint64_t data_=0,metadata_=0,sections_=0;
public:
    explicit SnapshotLayoutWitness(ggml_backend_buffer_type_t expected):expected_(expected){
        if(!expected_)throw std::invalid_argument("An original GPU buffer type is required");
        alignment_=ggml_backend_buft_get_alignment(expected_);
        if(!alignment_||alignment_>65536||(alignment_&(alignment_-1)))
            throw std::runtime_error("Snapshot buffer alignment is outside the qualified native range");
    }
    void write(const void*value,std::size_t bytes)override{
        if((bytes&&!value)||bytes>(1u<<20)||metadata_+bytes>(1u<<20))
            throw std::runtime_error("Snapshot metadata exceeds its original bound");
        metadata_+=bytes;
    }
    void write_tensor(ggml_tensor*t,std::size_t offset,std::size_t bytes)override{
        if(!t||t->type!=GGML_TYPE_F32||!t->buffer||ggml_backend_buffer_get_type(t->buffer)!=expected_||
           !bytes||bytes%alignment_||offset>ggml_nbytes(t)||bytes>ggml_nbytes(t)-offset||
           data_>(136ull<<20)||bytes>(136ull<<20)-data_||sections_>=512)
            throw std::runtime_error("Snapshot replacement requires complete aligned original F32 GPU slices");
        ggml_tensor copy{};copy.type=GGML_TYPE_F32;copy.ne[0]=std::int64_t(bytes/4);
        copy.nb[0]=4;for(unsigned i=1;i<4;++i){copy.ne[i]=1;copy.nb[i]=bytes;}
        if(ggml_backend_buft_get_alloc_size(expected_,&copy)!=bytes)
            throw std::runtime_error("Snapshot copied tensor has unqualified backend padding");
        data_+=bytes;++sections_;
    }
    std::size_t n_bytes()override{return std::size_t(data_+metadata_);}
    void require_exact_payload(std::uint64_t expected)const{
        if(!sections_||data_!=expected||data_>ggml_backend_buft_get_max_size(expected_))
            throw std::runtime_error("Actual complete snapshot layout differs from the priced single-buffer payload");
    }
    std::uint64_t tensor_bytes()const{return data_;}
    std::uint64_t tensor_sections()const{return sections_;}
    std::uint64_t metadata_bytes()const{return metadata_;}
};
}
