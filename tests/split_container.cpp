// SPDX-License-Identifier: MIT
// Exercise the actual startup inspection with full files and physical prefixes.
#include "direct_metadata.h"
#include "model_receipt.h"
#include "gguf.h"
#include "ggml.h"
#include <array>
#include <cstdio>
#include <filesystem>
#include <iostream>
#include <memory>
#include <unordered_set>
#include <vector>
using Json=nlohmann::json;
static void check(bool value,const char *message){if(!value)throw std::runtime_error(message);}
static std::uint64_t logical_bytes;
static unsigned parser_calls;
static std::vector<unsigned char> scratch_storage(qwen_app::metadata_direct_window+qwen_app::metadata_direct_alignment);
static void *scratch=reinterpret_cast<void*>((reinterpret_cast<std::uintptr_t>(scratch_storage.data())+
    qwen_app::metadata_direct_alignment-1)&~std::uintptr_t(qwen_app::metadata_direct_alignment-1));
struct HostRead final:qwen_app::MetadataReadOps {
    FILE *file;explicit HostRead(FILE *value):file(value){}
    std::int64_t read_at(void *target,std::size_t bytes,std::uint64_t offset)override{
        if(_fseeki64(file,static_cast<long long>(offset),SEEK_SET))return -1;
        return std::fread(target,1,bytes,file);
    }
    std::uint64_t now_ns()override{return 1;}
};
static std::size_t read_metadata(void *context,void *target,std::uint64_t offset,std::size_t bytes){
    return static_cast<qwen_app::DirectMetadataWindow*>(context)->read(target,offset,bytes);
}
static gguf_context *fixture_metadata(const char *path,gguf_init_params params){
    ++parser_calls;check(params.no_alloc,"Tensor payload allocation is prohibited");
    std::unique_ptr<FILE,decltype(&std::fclose)> file(std::fopen(path,"rb"),std::fclose);check(bool(file),"Metadata input unavailable");
    HostRead ops(file.get());qwen_app::DirectMetadataWindow window(ops,scratch,logical_bytes);
    auto *result=gguf_init_from_callback(read_metadata,&window,qwen_app::metadata_direct_window,logical_bytes,params);
    if(result){window.completed();check(window.logical_end<=gguf_get_data_offset(result),"Metadata parser consumed tensor payload");}
    return result;
}
// The generated header is the unmodified function extracted from native_main.
// Only its parser symbol is redirected to the real GGUF callback on the host.
#define gguf_init_from_file fixture_metadata
#include "native_container_inspection.h"
#undef gguf_init_from_file
template<class F>static void rejected(F f){bool failed=false;try{f();}catch(const std::exception&){failed=true;}check(failed,"Invalid physical/logical container admitted");}
static auto footprint(const qwen_app::ModelFootprint &v){return std::array<std::uint64_t,9>{v.device_weights,v.mapped_experts,v.lazy_ple,v.mapped_embeddings,v.skipped_mtp,v.mapped_files,v.largest_device_tensor,v.tensors,v.trunk_layers};}
int main(int argc,char **argv){try{
    check(argc==5,"Select receipt, metadata control, model directory and fresh fixture");
    std::ifstream input(argv[1]),control_input(argv[2]);Json receipt,control;input>>receipt;control_input>>control;
    check(receipt.at("files").size()==76&&control.at("files").size()==76,"All original GGUF inputs are required");
    const std::filesystem::path directory(argv[3]),fixture(argv[4]);check(!std::filesystem::exists(fixture),"A fresh fixture is required");
    constexpr std::uint64_t physical=512ull<<20;
    {std::ofstream out(fixture,std::ios::binary);out.seekp(static_cast<std::streamoff>(physical-1));out.put(0);check(bool(out),"Fixture extent failed");}
    qwen_app::ModelFootprint full,split;std::unordered_set<std::string> full_names,split_names;std::uint64_t total=0,prefix_bytes=0;
    for(std::size_t i=0;i<76;++i){
        const auto &row=receipt.at("files")[i];const auto name=row.at("path").get<std::string>();const auto bytes=row.at("bytes").get<std::uint64_t>();
        check(bytes>physical,"This control expects full first physical parts");
        const auto found=std::find_if(control.at("files").begin(),control.at("files").end(),[&](const Json &v){return v.at("name")==name;});
        check(found!=control.at("files").end()&&found->at("metadata_identical")==true,"Original metadata qualification missing");
        const auto count=(found->at("metadata_bytes").get<std::uint64_t>()+qwen_app::metadata_direct_window-1)&~std::uint64_t(qwen_app::metadata_direct_window-1);
        check(count&&count<=qwen_app::metadata_direct_limit&&count<=physical,"Metadata prefix exceeds the qualified cap");
        std::vector<char> prefix(static_cast<std::size_t>(count));std::ifstream source(directory/name,std::ios::binary);source.read(prefix.data(),static_cast<std::streamsize>(count));check(source.gcount()==static_cast<std::streamsize>(count),"Original metadata prefix was short");
        {std::fstream out(fixture,std::ios::binary|std::ios::in|std::ios::out);out.write(prefix.data(),static_cast<std::streamsize>(count));out.flush();check(bool(out),"Fixture prefix write failed");}
        logical_bytes=bytes;inspect_container((directory/name).string(),i==0,full,full_names,bytes,bytes);
        inspect_container(fixture.string(),i==0,split,split_names,bytes,physical);
        check(footprint(full)==footprint(split)&&full_names==split_names,"Original metadata, spans or footprint changed");
        if(i==0){
            const auto calls=parser_calls;
            for(auto declared:{std::uint64_t(0),bytes}){qwen_app::ModelFootprint f;std::unordered_set<std::string> names;rejected([&]{inspect_container(fixture.string(),true,f,names,bytes,declared);});}
            std::filesystem::resize_file(fixture,physical-1);
            {qwen_app::ModelFootprint f;std::unordered_set<std::string> names;rejected([&]{inspect_container(fixture.string(),true,f,names,bytes,physical);});}
            check(parser_calls==calls,"Physical rejection accessed GGUF metadata");std::filesystem::resize_file(fixture,physical);
            logical_bytes=physical;{qwen_app::ModelFootprint f;std::unordered_set<std::string> names;rejected([&]{inspect_container(fixture.string(),true,f,names,physical,physical);});}logical_bytes=bytes;
        }
        total=qwen_app::checked_memory_sum(total,bytes);prefix_bytes+=count;
    }
    qwen_app::validate_original_footprint(full,total);qwen_app::validate_original_footprint(split,total);
    std::cout<<Json{{"logical_files",76},{"logical_bytes",total},{"physical_first_part_bytes",physical},
        {"original_footprints_and_tensor_names_equal",true},{"all_original_experts_and_PLE_retained",true},
        {"metadata_prefix_bytes_copied",prefix_bytes},{"physical_and_logical_refusals",4},{"learned_inference",false},{"GPU_calls",0}}.dump()<<'\n';return 0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
