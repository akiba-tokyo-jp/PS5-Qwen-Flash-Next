// SPDX-License-Identifier: MIT
// The actual codec, resource registry and lookup tables run with host heap I/O.
#include "shader_assets.h"
#include "system_memory.h"
#include "profile_clock.h"
#include <ps5platform/heap.h>
#include "ggml-vulkan-shaders.hpp"
#include "shader_codec_sample.h"
#include <atomic>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <mutex>
#include <thread>
#include <vector>
namespace {
std::mutex heap_mutex;std::map<const void*,std::size_t> allocations;
std::size_t live=0,peak=0;bool refuse_heap=false;
void check(bool ok,const char *m){if(!ok)throw std::runtime_error(m);}
}
extern "C" void *ps5_heap_memalign(std::size_t,std::size_t size) {
    if(refuse_heap)return nullptr;void *p=std::malloc(size);if(!p)return nullptr;
    std::lock_guard<std::mutex> lock(heap_mutex);allocations[p]=size;live+=size;peak=std::max(peak,live);return p;
}
extern "C" void *ps5_heap_calloc(std::size_t n,std::size_t bytes){void*p=ps5_heap_memalign(16,n*bytes);if(p)std::memset(p,0,n*bytes);return p;}
extern "C" bool ps5_heap_owns(const void*p){std::lock_guard<std::mutex>lock(heap_mutex);return allocations.count(p)!=0;}
extern "C" void ps5_heap_free(void*p){std::lock_guard<std::mutex>lock(heap_mutex);const auto it=allocations.find(p);check(it!=allocations.end(),"Unknown codec allocation released");live-=it->second;allocations.erase(it);std::free(p);}
extern "C" void ps5_heap_stats(struct ps5_heap_stats *s){std::lock_guard<std::mutex>lock(heap_mutex);*s={};s->mapped_bytes=live;s->peak_bytes=peak;}
namespace qwen_app {
SystemMemoryObservation observe_native_system_memory(){SystemMemoryObservation s;s.page_size=16384;s.kernel_pages=138739;s.kernel_free=5000;s.kernel_minimum=898;s.kernel_target=2974;s.kernel_reserved=206;s.flexible_available=1ull<<30;return s;}
}
int main(int argc,char **argv){try{
    check(argc==2,"Select one shader storage control");const std::string mode=argv[1];
    if(mode=="heap_refusal")refuse_heap=true;
    bool rejected=false;
    try{qwen_app::initialize_native_shader_assets();}catch(const std::exception&){rejected=true;}
    if(mode=="heap_refusal") {
        check(rejected&&qwen_app::native_shader_asset_stats().failed,"Heap refusal admitted shader code");
        std::cout<<mode<<" passed\n"<<std::flush;std::_Exit(0);
    }
    check(!rejected,"Actual shader codec initialization failed");
    if(mode=="normal"||mode=="concurrent") {
        const auto s=qwen_app::verify_native_shader_assets_CPU();
        check(s.assets==QWEN_EXPECTED_SHADER_COUNT&&s.CPU_verified_assets==s.assets&&
            s.lookup_entries==QWEN_EXPECTED_LOOKUP_COUNT&&s.CPU_verified_lookups==s.lookup_entries&&
            s.stored_bytes==QWEN_EXPECTED_STORED_BYTES&&s.codec_output_bytes==QWEN_EXPECTED_OUTPUT_BYTES&&
            s.codec_ordering_bytes==QWEN_EXPECTED_OUTPUT_BYTES&&
            s.registry_sha256==QWEN_EXPECTED_SHADER_REGISTRY&&!s.active_lease&&!s.failed,
            "Original shader bytes or lookup table mapping changed");
        if(mode=="concurrent") {
            std::atomic<bool> bad{false};std::vector<std::thread> workers;
            for(unsigned i=0;i<8;++i)workers.emplace_back([&]{try{for(unsigned j=0;j<16;++j){
                std::size_t n=0;void *lease=nullptr;const auto*p=static_cast<const unsigned char*>(qwen_app_prepare_shader_code(QWEN_CODEC_SAMPLE_DATA,QWEN_CODEC_SAMPLE_SIZE,&n,&lease));
                std::vector<unsigned char> copy(p,p+n);std::this_thread::sleep_for(std::chrono::milliseconds(1));
                check(!std::memcmp(copy.data(),p,n),"Another producer overwrote active shader input");qwen_app_complete_shader_code(lease);
            }}catch(...){bad=true;}});
            for(auto&t:workers)t.join();check(!bad,"Exclusive concurrent shader ownership failed");
        }
        const auto final=qwen_app::native_shader_asset_stats();check(!final.failed&&!final.active_lease,"Positive codec ownership did not retire");
        std::cout<<mode<<" all original shader bytes/lookups passed\n";return 0;
    }
    std::vector<unsigned char> broken(QWEN_CODEC_SAMPLE_DATA,QWEN_CODEC_SAMPLE_DATA+QWEN_CODEC_SAMPLE_SIZE);
    std::size_t n=0;void*lease=nullptr;
    if(mode=="wrong_owner"||mode=="unknown_owner") {
        (void)qwen_app_prepare_shader_code(broken.data(),broken.size(),&n,&lease);check(lease,"The sample must exercise compressed ownership");
        if(mode=="wrong_owner") {
            std::atomic<bool> refused{false};std::thread other([&]{try{qwen_app_complete_shader_code(lease);}catch(...){refused=true;}});other.join();check(refused,"A foreign producer retired shader input");
        }else {
            const auto start=qwen_app::ProfileClock::now();bool timed_out=false;
            try{void*second=nullptr;(void)qwen_app_prepare_shader_code(broken.data(),broken.size(),&n,&second);}catch(...){timed_out=true;}
            const auto ns=qwen_app::profile_elapsed_ns(start);check(timed_out&&ns>=10000000000ull&&ns<13000000000ull,"Unknown shader ownership did not stop at its finite boundary");
        }
        const auto s=qwen_app::native_shader_asset_stats();check(s.failed&&s.active_lease,"Unknown/foreign ownership released its backing");
    }else {
        if(mode=="checksum")broken[16]^=1;
        else if(mode=="length")std::memset(broken.data()+8,0xff,4);
        else if(mode=="format")broken[0]^=1;
        else throw std::runtime_error("Unknown shader control");
        bool refused=false;try{(void)qwen_app_prepare_shader_code(broken.data(),broken.size(),&n,&lease);}catch(...){refused=true;}
        check(refused&&qwen_app::native_shader_asset_stats().failed,"Corrupt shader code was admitted");
        refused=false;try{(void)qwen_app_prepare_shader_code(QWEN_CODEC_SAMPLE_DATA,QWEN_CODEC_SAMPLE_SIZE,&n,&lease);}catch(...){refused=true;}
        check(refused,"A failed shader restoration retried");
    }
    std::cout<<mode<<" retention/quarantine passed\n"<<std::flush;std::_Exit(0);
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
