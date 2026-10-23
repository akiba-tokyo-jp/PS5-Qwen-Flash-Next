// SPDX-License-Identifier: MIT
// Host-only integration fixture: real GGML kernels, no learned model or GPU.
#include "mapped_source.h"
#include "mapped_source_bridge.h"
#include "ggml.h"
#include "ggml-backend.h"
#include "ggml-cpu.h"
#include "ggml-cpu-impl.h"
#include "ops.h"
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <array>
#include <fstream>
#include <iostream>
#include <memory>

using namespace qwen_app;
struct Reads final : SourceReadOps {
    alignas(64) std::array<unsigned char,1048576> bytes{};
    SourceIdentity key{1,7,0100644,0,0,1048576,123,0,123,0};
    unsigned reads=0;
    SourceIdentity identity(int) override { return key; }
    int open_direct(const std::string &) override { return 8; }
    bool close_file(int) override { return true; }
    std::uint64_t os_free() override { return 2ull<<30; }
    std::int64_t read_at(int,void * target,std::size_t size,std::uint64_t offset) override {
        if (size>model_read_window || size%16384 || offset%16384 || offset>=bytes.size())
            throw std::runtime_error("Unbounded synthetic CPU read");
        const auto count=std::min<std::uint64_t>(size,bytes.size()-offset);
        std::memcpy(target,bytes.data()+offset,count);++reads;return count;
    }
};
static std::unique_ptr<MappedSourceReader> source;
extern "C" bool qwen_app_model_reads_enabled() { return bool(source); }
extern "C" bool qwen_app_model_compute_limits_enabled() { return bool(source); }
extern "C" bool qwen_app_model_source_range_metadata(const void * at,std::size_t bytes) {
    return source && source->contains_metadata(reinterpret_cast<std::uintptr_t>(at),bytes);
}
extern "C" const void * qwen_app_model_source_chunk(const void * at,std::size_t wanted,std::size_t * copied) {
    return source->prepare(reinterpret_cast<std::uintptr_t>(at),wanted,*copied);
}
extern "C" void qwen_app_model_source_chunk_completed() { source->completed(); }
extern "C" void qwen_app_model_source_read_CPU(void * target,const void * at,std::size_t bytes) {
    if (qwen_app_model_source_range_metadata(target,bytes)) throw std::runtime_error("Reserved destination is read-only");
    for(std::size_t done=0;done<bytes;) {
        std::size_t count=0;const void * window=source->prepare(reinterpret_cast<std::uintptr_t>(at)+done,bytes-done,count);
        std::memcpy(static_cast<unsigned char *>(target)+done,window,count);source->completed();done+=count;
    }
}
static void check(bool value) { if(!value)throw std::runtime_error("Original CPU row/copy integration mismatch"); }
int main(int argc,char ** argv) {
    try {
        check(argc==2);std::ofstream output(argv[1],std::ios::binary|std::ios::trunc);check(bool(output));
        unsigned rows_checked=0,copies_checked=0,graphs_checked=0;
        for(const unsigned columns : {8u,2560u,7680u}) for(const auto type : {GGML_TYPE_BF16,GGML_TYPE_F32}) {
            auto owned_reads=std::make_unique<Reads>();auto & reads=*owned_reads;
            const std::size_t element=type==GGML_TYPE_BF16?2:4,offset=256;
            for(unsigned i=0;i<columns*7*2*2;++i) {
                const float value=(int(i)-100)*.25f+(type==GGML_TYPE_F32?.1f:0.f);
                std::uint32_t bits;std::memcpy(&bits,&value,4);
                if(element==2){const std::uint16_t raw=bits>>16;std::memcpy(reads.bytes.data()+offset+i*2,&raw,2);}
                else std::memcpy(reads.bytes.data()+offset+i*4,&value,4);
            }
            std::vector<unsigned char> scratch_bytes(model_read_window+model_read_alignment);
            const auto scratch=(reinterpret_cast<std::uintptr_t>(scratch_bytes.data())+16383)&~std::uintptr_t(16383);
            void * reserved=nullptr;void * tensor_data=reads.bytes.data()+offset;
#ifdef TEST_RESERVED_SOURCE
            reserved=VirtualAlloc(nullptr,reads.bytes.size(),MEM_RESERVE,PAGE_NOACCESS);check(reserved);
            source=std::make_unique<MappedSourceReader>(std::vector<SourceFile>{{"synthetic-original",reads.bytes.size(),reads.key}},reads,reinterpret_cast<void *>(scratch));
            source->register_mapping(reinterpret_cast<std::uintptr_t>(reserved),reads.bytes.size(),4);
            tensor_data=static_cast<unsigned char *>(reserved)+offset;
#endif
            auto * context=ggml_init({2u<<20,nullptr,true});check(context);
            auto * weights=ggml_new_tensor_4d(context,type,columns,7,2,2);weights->data=tensor_data;
            auto * indices=ggml_new_tensor_3d(context,GGML_TYPE_I32,3,2,2);
            std::array<int32_t,12> ids{};for(unsigned i=0;i<ids.size();++i)ids[i]=(i*3+1)%7;indices->data=ids.data();
            auto * result=ggml_get_rows(context,weights,indices);std::vector<float> actual(columns*12);result->data=actual.data();
            ggml_compute_params params{};params.nth=1;params.ith=0;
            std::cerr<<"fixture stage=gather type="<<int(type)<<'\n';
#ifdef TEST_RESERVED_SOURCE
            const auto before=reads.reads;params.ith=1;params.nth=2;
            std::thread worker([&]{ggml_compute_forward_get_rows(&params,result);});worker.join();
            check(reads.reads==before);for(auto value:actual)check(value==0);
            params.ith=0;params.nth=1;
#endif
            ggml_compute_forward_get_rows(&params,result);
            for(unsigned row=0;row<ids.size();++row)for(unsigned column=0;column<columns;++column) {
                const unsigned z=row/6,y=(row-z*6)/3,index=((z*2+y)*7+ids[row])*columns+column;
                float expected;
                if(element==2){std::uint16_t raw;std::memcpy(&raw,reads.bytes.data()+offset+index*2,2);const std::uint32_t bits=std::uint32_t(raw)<<16;std::memcpy(&expected,&bits,4);}
                else std::memcpy(&expected,reads.bytes.data()+offset+index*4,4);
                check(std::memcmp(&expected,&actual[row*columns+column],4)==0);++rows_checked;
            }
            const auto direct_result=actual;std::fill(actual.begin(),actual.end(),0);
            std::cerr<<"fixture stage=three-thread-graph type="<<int(type)<<'\n';
            auto * graph=ggml_new_graph(context);ggml_build_forward_expand(graph,result);
            check(ggml_graph_compute_with_ctx(context,graph,3)==GGML_STATUS_SUCCESS);
            check(std::memcmp(direct_result.data(),actual.data(),actual.size()*sizeof(float))==0);++graphs_checked;
            output.write(reinterpret_cast<const char *>(actual.data()),actual.size()*sizeof(float));
            auto * buffer=ggml_backend_cpu_buffer_from_ptr(tensor_data,ggml_nbytes(weights));weights->buffer=buffer;
            std::cerr<<"fixture stage=buffer-get type="<<int(type)<<'\n';
            std::vector<unsigned char> copied(ggml_nbytes(weights));ggml_backend_tensor_get(weights,copied.data(),0,copied.size());
            check(!std::memcmp(copied.data(),reads.bytes.data()+offset,copied.size()));++copies_checked;
            auto * copy=ggml_new_tensor_4d(context,type,columns,7,2,2);std::vector<unsigned char> destination_storage(copied.size()+64);
            auto * destination=reinterpret_cast<unsigned char *>((reinterpret_cast<std::uintptr_t>(destination_storage.data())+63)&~std::uintptr_t(63));copy->data=destination;
            auto * destination_buffer=ggml_backend_cpu_buffer_from_ptr(destination,copied.size());copy->buffer=destination_buffer;
            std::cerr<<"fixture stage=buffer-copy type="<<int(type)<<'\n';
            ggml_backend_tensor_copy(weights,copy);check(std::equal(copied.begin(),copied.end(),destination));++copies_checked;
            output.write(reinterpret_cast<const char *>(destination),copied.size());
#ifdef TEST_RESERVED_SOURCE
            auto * backend=ggml_backend_cpu_init();check(backend);
            check(ggml_backend_supports_op(backend,result));
            auto * unsafe_copy=ggml_dup(context,weights);
            check(!ggml_backend_supports_op(backend,unsafe_copy));ggml_backend_free(backend);
#endif
            ggml_backend_buffer_free(destination_buffer);ggml_backend_buffer_free(buffer);ggml_free(context);
            if(source){source->before_unmap(reinterpret_cast<std::uintptr_t>(reserved),reads.bytes.size());source->after_unmap(reinterpret_cast<std::uintptr_t>(reserved),reads.bytes.size());source->close_completed();source.reset();check(VirtualFree(reserved,0,MEM_RELEASE));}
        }
        check(bool(output));std::cout<<"Real BF16/F32 CPU elements="<<rows_checked<<" exact, graphs with three threads="<<graphs_checked<<", buffer copies="<<copies_checked<<", model inference=0\n";
    }catch(const std::exception & error){std::cerr<<error.what()<<'\n';return 1;}
}
