// SPDX-License-Identifier: MIT
// Compile the actual patched POSIX mmap implementation with controlled APIs.
#include "mapped_source_bridge.h"
#include "source_virtual_addresses.h"
#include "virtual_source.h"
#include "nlohmann/json.hpp"
#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#define _POSIX_MAPPED_FILES 1
#define MAP_SHARED 1
#define PROT_READ 1
#define MAP_FAILED reinterpret_cast<void *>(~std::uintptr_t(0))
#define POSIX_MADV_WILLNEED 1
#define POSIX_MADV_RANDOM 2
#define _SC_PAGESIZE 1
static bool enabled=true;
static unsigned registered=0,released=0,before_unmap=0,after_unmap=0,ordinary_maps=0,ordinary_unmaps=0,advice=0;
static qwen_app::SourceVirtualAddresses addresses;
static void check(bool v){if(!v)throw std::runtime_error("Actual mmap source lifetime invariant failed");}
extern "C" bool qwen_app_model_reads_enabled(){return enabled;}
extern "C" void *qwen_app_model_source_reserve_virtual(std::size_t bytes){return reinterpret_cast<void *>(addresses.claim(qwen_app::virtual_source_span(bytes)));}
extern "C" int qwen_app_model_source_release_virtual(void *at,std::size_t bytes){
    const auto key=reinterpret_cast<std::uintptr_t>(at),span=qwen_app::virtual_source_span(bytes);
    check(enabled&&addresses.owned(key)==span);addresses.retire(key,span);++released;return 0;
}
extern "C" void qwen_app_model_mapping_open(void *,std::size_t,int fd){check(fd==7);++registered;}
extern "C" void qwen_app_model_mapping_before_unmap(void *,std::size_t){++before_unmap;}
extern "C" void qwen_app_model_mapping_after_unmap(void *,std::size_t){++after_unmap;}
static long fixture_sysconf(int kind){check(kind==_SC_PAGESIZE);return 16384;}
static void *fixture_mmap(void *,std::size_t,int,int,int fd,std::int64_t){check(!enabled&&fd==7);++ordinary_maps;return reinterpret_cast<void *>(0x10000000);}
static int fixture_munmap(void *,std::size_t){check(!enabled);++ordinary_unmaps;return 0;}
static int fixture_madvise(void *,std::size_t,int){check(!enabled);++advice;return 0;}
static std::string format(const char *,...){return "fixture mmap failure";}
static void fixture_warn(const char *,...){}
[[noreturn]] static void invariant_abort(){std::abort();}
#define sysconf fixture_sysconf
#define mmap fixture_mmap
#define munmap fixture_munmap
#define posix_madvise fixture_madvise
#define LLAMA_LOG_WARN(...) fixture_warn(__VA_ARGS__)
#define GGML_ASSERT(value) check(value)
#define GGML_ABORT(...) invariant_abort()
struct llama_file {std::size_t bytes;std::size_t size()const{return bytes;}int file_id()const{return 7;}};
struct llama_mmap {using ranges=std::vector<std::pair<std::size_t,std::size_t>>;struct impl;};
static llama_mmap::ranges ranges_complement(const llama_mmap::ranges &,std::size_t){return {};}
#include "actual_reserved_mmap_impl.h"
int main(int argc,char **argv){
    check(argc==2);std::ifstream stream(argv[1]);nlohmann::json receipt;stream>>receipt;
    std::vector<std::unique_ptr<llama_mmap::impl>> maps;std::uint64_t total=0;
    for(const auto &row:receipt.at("files")){
        const auto bytes=row.at("bytes").get<std::size_t>();llama_file file{bytes};
        auto map=std::make_unique<llama_mmap::impl>(&file,0,false,llama_mmap::ranges{});
        map->unmap_fragment(0,65536);map->unmap_fragment(bytes/3,bytes/3+(1u<<20));
        map->unmap_fragment(bytes-(1u<<20),bytes);map->unmap_fragment(0,bytes);
        check(map->mapped_fragments.size()==1&&map->mapped_fragments.front()==std::make_pair(std::size_t(0),bytes));
        check(!released&&!before_unmap&&!after_unmap&&!ordinary_maps&&!ordinary_unmaps&&!advice);
        total+=bytes;maps.push_back(std::move(map));
    }
    check(maps.size()==76&&total==359246956672ull&&registered==76);maps.clear();
    check(released==76&&before_unmap==76&&after_unmap==76&&!ordinary_unmaps);
    const auto first=addresses.claim(16384);check(first==qwen_app::source_key_base);addresses.retire(first,16384);
    enabled=false;llama_file ordinary{65536};
    {llama_mmap::impl map(&ordinary,0,false,{});map.unmap_fragment(16384,32768);check(ordinary_unmaps==1&&map.mapped_fragments.size()==2);}
    check(ordinary_maps==1&&ordinary_unmaps==3&&released==76&&before_unmap==79&&after_unmap==79);
    std::cout<<"Actual patched mmap: 76 original spans retain complete virtual keys through 304 trim requests, release exactly once at destruction, and preserve ordinary mmap fragment behavior\n";
}
