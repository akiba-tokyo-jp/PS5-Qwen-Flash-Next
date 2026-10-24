// SPDX-License-Identifier: MIT
// Compare the actual GGUF parser through its original and fixed-window readers.
#include "direct_metadata.h"
#include "gguf.h"
#include "ggml.h"
#include <cstdio>
#include <iostream>
#include <memory>
#include <vector>
using namespace qwen_app;
static void check(bool v,const char *m){if(!v)throw std::runtime_error(m);}
template<class F>static void rejected(F f){bool failed=false;try{f();}catch(const std::exception&){failed=true;}check(failed,"Unsafe metadata operation admitted");}
struct Fake final:MetadataReadOps {
    std::vector<unsigned char> data;unsigned calls=0;int failure=0;std::uint64_t clock=1;
    explicit Fake(std::size_t n):data(n){for(std::size_t i=0;i<n;++i)data[i]=i%251;}
    std::int64_t read_at(void *target,std::size_t bytes,std::uint64_t offset)override {
        ++calls;check(!(bytes%metadata_direct_alignment)&&!(offset%metadata_direct_alignment)&&bytes<=metadata_direct_window,"Unaligned metadata read");
        const auto count=std::min<std::size_t>(bytes,data.size()-offset);std::memcpy(target,data.data()+offset,count);
        if(failure==1)return std::int64_t(count)-1;if(failure==2)return -1;if(failure==3)clock+=20000000001ull;
        return count;
    }
    std::uint64_t now_ns()override{return ++clock;}
};
struct FileOps final:MetadataReadOps {
    FILE *file;explicit FileOps(FILE*f):file(f){}
    std::int64_t read_at(void *at,std::size_t bytes,std::uint64_t offset)override {
        if(_fseeki64(file,static_cast<long long>(offset),SEEK_SET))return -1;
        return std::fread(at,1,bytes,file);
    }
    std::uint64_t now_ns()override{return 1;}
};
static std::size_t callback(void *context,void *out,std::uint64_t offset,std::size_t bytes){return static_cast<DirectMetadataWindow*>(context)->read(out,offset,bytes);}
int main(int argc,char **argv){try{
    std::vector<unsigned char> raw(metadata_direct_window+metadata_direct_alignment);
    auto *scratch=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(raw.data())+metadata_direct_alignment-1)&~std::uintptr_t(metadata_direct_alignment-1));
    if(argc==1) {
        Fake ops(2*metadata_direct_window+37);DirectMetadataWindow reader(ops,scratch,ops.data.size());
        std::vector<unsigned char> out(100000);
        reader.read(out.data(),17,out.size());check(ops.calls==1,"Metadata prefix was not cached");
        reader.read(out.data(),25,13);check(ops.calls==1,"Tiny parser fields repeated physical I/O");
        const auto offset=metadata_direct_window-200;reader.read(out.data(),offset,out.size());
        for(std::size_t i=0;i<out.size();++i)check(out[i]==(offset+i)%251,"Cross-window original byte changed");
        reader.read(out.data(),2*metadata_direct_window+20,17);reader.completed();
        check(ops.calls==3&&reader.physical_bytes==ops.data.size(),"Exact EOF-tail accounting changed");
        for(int mode=1;mode<=6;++mode){Fake failing(2*metadata_direct_window+37);DirectMetadataWindow r(failing,scratch,failing.data.size());failing.failure=mode;
            rejected([&]{if(mode==4)r.read(out.data(),0,0);else if(mode==5)r.read(out.data(),failing.data.size(),1);
                else if(mode==6)r.read(out.data(),0,metadata_direct_window+1);else r.read(out.data(),0,16);});
            const auto calls=failing.calls;rejected([&]{r.read(out.data(),0,16);});check(calls==failing.calls,"Failed read retried");}
        Fake huge(1);DirectMetadataWindow bounded(huge,scratch,metadata_direct_limit+1);
        rejected([&]{bounded.read(out.data(),metadata_direct_limit,1);});
        std::cout<<"Exact bytes, cache boundaries, EOF, deadline, failures and quarantine passed\n";return 0;
    }
    check(argc==2,"Select one original GGUF file");
    std::unique_ptr<FILE,decltype(&std::fclose)> file(std::fopen(argv[1],"rb"),std::fclose);check(bool(file),"Original GGUF unavailable");
    check(!_fseeki64(file.get(),0,SEEK_END),"Original GGUF size seek failed");const auto bytes=_ftelli64(file.get());check(bytes>0,"Original GGUF empty");
    ggml_context *first_heap=nullptr,*second_heap=nullptr;
    std::unique_ptr<gguf_context,decltype(&gguf_free)> first(gguf_init_from_file(argv[1],{true,&first_heap}),gguf_free);
    FileOps ops(file.get());DirectMetadataWindow reader(ops,scratch,std::uint64_t(bytes));
    std::unique_ptr<gguf_context,decltype(&gguf_free)> second(gguf_init_from_callback(callback,&reader,metadata_direct_window,std::uint64_t(bytes),{true,&second_heap}),gguf_free);
    check(first&&second&&first_heap&&second_heap,"Original parser/context did not complete");reader.completed();
    const auto count=gguf_get_meta_size(first.get());check(count==gguf_get_meta_size(second.get()),"Original metadata size changed");
    std::vector<unsigned char> a(count),b(count);gguf_get_meta_data(first.get(),a.data());gguf_get_meta_data(second.get(),b.data());
    check(a==b&&ggml_used_mem(first_heap)==ggml_used_mem(second_heap),"Original GGUF metadata or GGML context changed");
    check(reader.logical_end<=gguf_get_data_offset(second.get()),"Parser escaped original metadata");
    std::cout<<"{\"metadata_bytes\":"<<count<<",\"physical_bytes\":"<<reader.physical_bytes<<",\"physical_reads\":"<<reader.physical_reads<<",\"metadata_identical\":true,\"GGML_context_identical\":true}\n";
    first.reset();second.reset();ggml_free(first_heap);ggml_free(second_heap);
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
