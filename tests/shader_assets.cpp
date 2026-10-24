// SPDX-License-Identifier: MIT
// The actual codec, resource registry and lookup tables run with host heap I/O.
#include "shader_assets.h"
#include "system_memory.h"
#include "memory_backpressure.h"
#include "profile_clock.h"
#include <ps5platform/heap.h>
#include "ggml-vulkan-shaders.hpp"
#include "shader_codec_sample.h"
#include "shader_file_fixture.h"
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
std::map<const void*,void*> allocation_backing;
std::size_t live=0,peak=0;bool refuse_heap=false;
void check(bool ok,const char *m){if(!ok)throw std::runtime_error(m);}
void check_guards() {
    for(const auto &item:allocations) {
        const auto *p=static_cast<const unsigned char*>(item.first);
        for(std::size_t i=0;i<64;++i)check(p[-int(i)-1]==0xa5&&p[item.second+i]==0xa5,"Codec exceeded its tracked buffer");
    }
}
}
extern "C" void *ps5_heap_memalign(std::size_t alignment,std::size_t size) {
    if(refuse_heap||!alignment||(alignment&(alignment-1)))return nullptr;
    auto *raw=static_cast<unsigned char*>(std::malloc(size+alignment+128));if(!raw)return nullptr;
    std::memset(raw,0xa5,size+alignment+128);
    const auto at=(reinterpret_cast<std::uintptr_t>(raw+64)+alignment-1)&~std::uintptr_t(alignment-1);void *p=reinterpret_cast<void*>(at);
    std::lock_guard<std::mutex> lock(heap_mutex);allocations[p]=size;allocation_backing[p]=raw;live+=size;peak=std::max(peak,live);return p;
}
extern "C" void *ps5_heap_calloc(std::size_t n,std::size_t bytes){void*p=ps5_heap_memalign(16,n*bytes);if(p)std::memset(p,0,n*bytes);return p;}
extern "C" bool ps5_heap_owns(const void*p){std::lock_guard<std::mutex>lock(heap_mutex);return allocations.count(p)!=0;}
extern "C" void ps5_heap_free(void*p){std::lock_guard<std::mutex>lock(heap_mutex);const auto it=allocations.find(p);check(it!=allocations.end(),"Unknown codec allocation released");check_guards();live-=it->second;allocations.erase(it);std::free(allocation_backing.at(p));allocation_backing.erase(p);}
extern "C" void ps5_heap_stats(struct ps5_heap_stats *s){std::lock_guard<std::mutex>lock(heap_mutex);check_guards();*s={};s->mapped_bytes=live;s->peak_bytes=peak;}
namespace qwen_app {
namespace {
MemoryBackpressure startup_gate;
std::string startup_mode;
std::uint64_t admission_clock=1,admission_pauses=0,admission_observations=0;
}
SystemMemoryObservation observe_native_system_memory(){
    SystemMemoryObservation s;s.page_size=16384;s.kernel_pages=138739;s.kernel_free=5000;
    s.kernel_minimum=898;s.kernel_target=2974;s.kernel_reserved=206;s.flexible_available=1ull<<30;
    if(startup_mode=="startup_pressure"||(startup_mode=="startup_recovery"&&admission_pauses<2))s.kernel_free=1000;
    if(startup_mode=="startup_invalid")s.page_size=4096;
    return s;
}
SystemMemoryObservation admit_native_system_memory(){
    struct Ops final:MemoryAdmissionOps {
        SystemMemoryObservation observe()override{++admission_observations;return observe_native_system_memory();}
        std::uint64_t now_ns()override{return admission_clock;}
        void pause_ns(std::uint64_t ns)override{admission_clock+=ns;++admission_pauses;}
    }ops;
    return startup_gate.admit(ops);
}
}
int main(int argc,char **argv){try{
    check(argc==2||argc==3,"Select one shader storage control and optional exact file fixture");const std::string mode=argv[1];
    qwen_app::startup_mode=mode;qwen_app::startup_gate.enable();
    if(mode=="heap_refusal")refuse_heap=true;
    bool rejected=false;
    const bool external=qwen_app::native_shader_file_registered();
    if(external){check(argc==3,"External resources require their exact original file fixture");configure_shader_file_fixture(argv[2],mode);}
    try{
        if(external&&mode!="file_unverified") {
            std::string sha=QWEN_EXPECTED_FILE_SHA256;
            if(mode=="file_wrong_sha")sha[0]=sha[0]=='0'?'1':'0';
            std::string path="/app0/qwen-runtime/shader-storage-"+sha+".bin";
            if(mode=="file_wrong_path")path+=".unexpected";
            const auto bytes=QWEN_EXPECTED_FILE_BYTES+(mode=="file_wrong_size"?4u:0u);
            qwen_app::initialize_native_shader_file(path,bytes,sha);
            if(mode=="file_duplicate_configuration")qwen_app::initialize_native_shader_file(path,bytes,sha);
        }
        qwen_app::initialize_native_shader_assets();
    }catch(const std::exception&){rejected=true;}
    const bool file_refusal=mode=="file_corrupt"||mode=="file_short"||mode=="file_oversized"||mode=="file_pending"||
        mode=="file_startup_guard"||mode=="file_identity_during_read"||mode=="file_timeout"||mode=="file_wrong_sha"||
        mode=="file_wrong_size"||mode=="file_wrong_path"||mode=="file_duplicate_configuration"||mode=="file_unverified";
    if(file_refusal) {
        const auto s=qwen_app::native_shader_asset_stats();check(external&&rejected&&s.failed,"Unqualified external file was admitted");
        check(s.external_file.read_pending==(mode=="file_pending"),"Unknown external read was not retained");
        const auto calls=shader_file_fixture_calls();bool repeat=false;
        if(mode=="file_wrong_sha"||mode=="file_wrong_path"||mode=="file_wrong_size"||mode=="file_unverified")
            check(calls==0&&peak==0,"Invalid external file policy allocated or read payload");
        try{qwen_app::initialize_native_shader_file("/app0/qwen-runtime/shader-storage-" QWEN_EXPECTED_FILE_SHA256 ".bin",QWEN_EXPECTED_FILE_BYTES,QWEN_EXPECTED_FILE_SHA256);}catch(...){repeat=true;}
        check(repeat&&shader_file_fixture_calls()==calls,"Failed external file admission retried");
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        std::cout<<mode<<" external admission refusal/retention passed\n"<<std::flush;std::_Exit(0);
    }
    if(mode=="startup_pressure"||mode=="startup_invalid") {
        const auto s=qwen_app::native_shader_asset_stats();
        check(rejected&&!s.initialized&&!s.active_lease&&live==0&&peak==0,"Startup pressure allocated codec storage");
        const auto observations=qwen_app::admission_observations;
        bool refused=false;try{qwen_app::initialize_native_shader_assets();}catch(...){refused=true;}
        check(refused&&qwen_app::admission_observations==observations&&live==0,"Failed startup admission retried");
        if(mode=="startup_pressure")check(qwen_app::admission_pauses==200&&
            qwen_app::startup_gate.stats().wait_ns==20000000000ull,"Shader startup escaped the existing boundary wait");
        else check(qwen_app::admission_pauses==0,"Invalid memory counters were polled as pressure");
        std::cout<<mode<<" bounded admission without allocation passed\n";return 0;
    }
    if(mode=="heap_refusal") {
        check(rejected&&qwen_app::native_shader_asset_stats().failed,"Heap refusal admitted shader code");
        std::cout<<mode<<" passed\n"<<std::flush;std::_Exit(0);
    }
    check(!rejected,"Actual shader codec initialization failed");
    if(external) {
        const auto file=qwen_app::native_shader_file_stats();
        check(file.verified&&!file.failed&&!file.read_pending&&file.file_bytes==QWEN_EXPECTED_FILE_BYTES&&
            file.input_window_bytes==QWEN_EXPECTED_FILE_WINDOW,"Current whole-file SHA or tracked input window is missing");
    }
    if(mode=="startup_recovery")check(qwen_app::admission_pauses==2&&
        qwen_app::startup_gate.stats().recovered_admissions==1,"Shader startup bypassed bounded passive recovery");
    if(mode=="on_demand") {
        const auto before=qwen_app::native_shader_asset_stats();
        check(before.CPU_verified_assets==0&&before.CPU_verified_lookups==QWEN_EXPECTED_LOOKUP_COUNT&&
            before.decoded_calls==0&&before.raw_calls==0,"Metadata admission decoded unused shader storage");
        std::size_t bytes=0;void *lease=nullptr;
        const auto *p=static_cast<const unsigned char*>(qwen_app_prepare_shader_code(QWEN_CODEC_SAMPLE_DATA,QWEN_CODEC_SAMPLE_SIZE,&bytes,&lease));
        check(bytes>=20&&p[0]==3&&p[1]==2&&p[2]==35&&p[3]==7,"On-demand restoration changed original SPIR-V");
        qwen_app_complete_shader_code(lease);const auto after=qwen_app::native_shader_asset_stats();
        check(after.decoded_calls==1&&after.raw_calls==0&&after.CPU_verified_assets==0&&
            !after.active_lease&&!after.failed,"On-demand original bytes did not complete with their exclusive lease");
        std::cout<<mode<<" current lookups and per-use exact SHA256 passed\n";return 0;
    }
    if(mode=="normal"||mode=="concurrent"||mode=="startup_recovery") {
        const auto s=qwen_app::verify_native_shader_assets_CPU();
        check(s.assets==QWEN_EXPECTED_SHADER_COUNT&&s.CPU_verified_assets==s.assets&&
            s.lookup_entries==QWEN_EXPECTED_LOOKUP_COUNT&&s.CPU_verified_lookups==s.lookup_entries&&
            s.stored_bytes==QWEN_EXPECTED_STORED_BYTES&&s.codec_output_bytes==QWEN_EXPECTED_OUTPUT_BYTES&&
            s.codec_ordering_bytes==QWEN_EXPECTED_ORDERING_BYTES&&
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
    if(external&&(mode=="file_changed_identity"||mode=="file_frame_checksum"||mode=="file_frame_timeout"||
                 mode=="file_frame_pressure"||mode=="file_unknown_location"||mode=="file_frame_quarantine")) {
        if(mode=="file_changed_identity")change_shader_file_fixture_identity();
        if(mode=="file_frame_checksum") {
            std::uint64_t offset=0;for(unsigned i=0;i<8;++i)offset|=std::uint64_t(QWEN_CODEC_SAMPLE_DATA[8+i])<<(8*i);
            corrupt_shader_file_fixture_byte(offset+16);
        }
        if(mode=="file_frame_timeout")delay_shader_file_fixture_read(11000000000ull);
        if(mode=="file_frame_pressure")pressure_shader_file_fixture();
        if(mode=="file_frame_quarantine")quarantine_shader_file_fixture_during_read();
        const void *input=QWEN_CODEC_SAMPLE_DATA;std::vector<unsigned char> copy;
        if(mode=="file_unknown_location"){copy.assign(QWEN_CODEC_SAMPLE_DATA,QWEN_CODEC_SAMPLE_DATA+24);input=copy.data();}
        std::size_t n=0;void *lease=nullptr;bool refused=false;
        try{(void)qwen_app_prepare_shader_code(input,QWEN_CODEC_SAMPLE_SIZE,&n,&lease);}catch(...){refused=true;}
        check(refused&&qwen_app::native_shader_asset_stats().failed,"Unqualified external module input was admitted");
        const auto calls=shader_file_fixture_calls();refused=false;
        try{(void)qwen_app_prepare_shader_code(QWEN_CODEC_SAMPLE_DATA,QWEN_CODEC_SAMPLE_SIZE,&n,&lease);}catch(...){refused=true;}
        check(refused&&shader_file_fixture_calls()==calls,"A failed external module input retried");
        struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
        std::cout<<mode<<" module-input refusal/retention passed\n"<<std::flush;std::_Exit(0);
    }
    std::vector<unsigned char> broken(QWEN_CODEC_SAMPLE_DATA,QWEN_CODEC_SAMPLE_DATA+(external?24:QWEN_CODEC_SAMPLE_SIZE));
    bool structured=false;
    for(const auto &fixture:bad_shader_frames)if(mode==fixture.mode){broken.assign(fixture.data,fixture.data+fixture.bytes);structured=true;}
    std::size_t n=0;void*lease=nullptr;
    if(mode=="wrong_owner"||mode=="unknown_owner") {
        const void*input=external?static_cast<const void*>(QWEN_CODEC_SAMPLE_DATA):broken.data();
        const auto input_bytes=external?QWEN_CODEC_SAMPLE_SIZE:broken.size();
        (void)qwen_app_prepare_shader_code(input,input_bytes,&n,&lease);check(lease,"The sample must exercise compressed ownership");
        if(mode=="wrong_owner") {
            std::atomic<bool> refused{false};std::thread other([&]{try{qwen_app_complete_shader_code(lease);}catch(...){refused=true;}});other.join();check(refused,"A foreign producer retired shader input");
        }else {
            const auto start=qwen_app::ProfileClock::now();bool timed_out=false;
            try{void*second=nullptr;(void)qwen_app_prepare_shader_code(input,input_bytes,&n,&second);}catch(...){timed_out=true;}
            const auto ns=qwen_app::profile_elapsed_ns(start);check(timed_out&&ns>=10000000000ull&&ns<13000000000ull,"Unknown shader ownership did not stop at its finite boundary");
        }
        const auto s=qwen_app::native_shader_asset_stats();check(s.failed&&s.active_lease,"Unknown/foreign ownership released its backing");
    }else {
        if(structured){}
        else if(mode=="checksum")broken[16]^=1;
        else if(mode=="length")std::memset(broken.data()+8,0xff,4);
        else if(mode=="format")broken[0]^=1;
        else throw std::runtime_error("Unknown shader control");
        bool refused=false;try{(void)qwen_app_prepare_shader_code(broken.data(),broken.size(),&n,&lease);}catch(...){refused=true;}
        check(refused&&qwen_app::native_shader_asset_stats().failed,"Corrupt shader code was admitted");
        refused=false;try{(void)qwen_app_prepare_shader_code(QWEN_CODEC_SAMPLE_DATA,QWEN_CODEC_SAMPLE_SIZE,&n,&lease);}catch(...){refused=true;}
        check(refused,"A failed shader restoration retried");
    }
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    std::cout<<mode<<" retention/quarantine passed\n"<<std::flush;std::_Exit(0);
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
