// SPDX-License-Identifier: MIT
#include "shader_file_native.h"
#include "model_cpu_budget.h"
#include "system_memory.h"
#include <ps5platform/heap.h>
#include <atomic>
#include <cstring>
#include <memory>
#include <stdexcept>
namespace {
const qwen_shader_file_plan *plan=nullptr;
std::atomic<bool> registration_fault{false},started{false},verified{false},failed{false},read_pending{false};
std::atomic<std::uint64_t> input_bytes{0},read_calls{0},returned_bytes{0},frame_requests{0};
std::unique_ptr<qwen_app::ShaderFileStore> store;
[[noreturn]] void refuse(const char*message){failed.store(true);throw std::runtime_error(message);}
void heap_admission() {
    struct ps5_heap_stats heap{};ps5_heap_stats(&heap);
    if(heap.libc_fallbacks||heap.mapped_bytes>qwen_app::maximum_model_CPU_heap_bytes||heap.peak_bytes>qwen_app::maximum_model_CPU_heap_bytes)
        refuse("External shader storage exceeds the existing tracked CPU heap budget");
}
class TrackedOps final:public qwen_app::ShaderFileOps {
    qwen_app::ShaderFileOps*source_=nullptr;
public:
    void bind(qwen_app::ShaderFileOps &source){if(source_)refuse("An external shader descriptor may only bind once");source_=&source;}
    std::array<std::uint64_t,10> identity()override{return source_->identity();}
    void system_headroom(bool startup)override{source_->system_headroom(startup);}
    std::uint64_t now_ns()override{return source_->now_ns();}
    void before_read()override{source_->before_read();read_pending.store(true);}
    std::int64_t read_at(void*at,std::size_t bytes,std::uint64_t offset)override {
        const auto got=source_->read_at(at,bytes,offset);++read_calls;
        if(got>0&&std::uint64_t(got)<=bytes)returned_bytes+=std::uint64_t(got);
        return got;
    }
    void read_returned()override{read_pending.store(false);source_->read_returned();}
};
TrackedOps source;
}
extern "C" void qwen_app_register_shader_file_plan(const qwen_shader_file_plan*value) {
    if(plan||!value||!value->bytes||value->bytes>(512ull<<20)||!value->input_window_bytes||
       value->input_window_bytes%qwen_app::shader_file_alignment||value->input_window_bytes>(2u<<20)) {
        registration_fault.store(true);return;
    }
    plan=value;
}
namespace qwen_app {
bool native_shader_file_registered(){return plan||registration_fault.load();}
void quarantine_native_shader_file(){if(native_shader_file_registered())failed.store(true);}
void initialize_native_shader_file(const std::string &path,std::uint64_t bytes,const std::string &sha) {
    if(started.exchange(true)||registration_fault.load()||!plan||failed.load())refuse("A fresh exact external shader file plan is required");
    try {
        if(bytes!=plan->bytes||sha.size()!=64||sha.find_first_not_of("0123456789abcdef")!=std::string::npos||
           path!="/app0/qwen-runtime/shader-storage-"+sha+".bin")
            refuse("External shader path, size or full SHA256 differs from the immutable plan");
        std::array<unsigned char,32> expected{};
        for(unsigned i=0;i<32;++i) {
            const auto digit=[](char c){return unsigned(c<='9'?c-'0':c-'a'+10);};
            expected[i]=static_cast<unsigned char>((digit(sha[2*i])<<4)|digit(sha[2*i+1]));
        }
        if(std::memcmp(expected.data(),plan->sha256,32))refuse("External shader file SHA256 differs from compiled resources");
        (void)admit_native_system_memory();heap_admission();
        void*window=ps5_heap_memalign(shader_file_alignment,plan->input_window_bytes);
        if(!window||!ps5_heap_owns(window))refuse("External shader input must use the existing tracked Direct CPU heap");
        input_bytes.store(plan->input_window_bytes);heap_admission();
        source.bind(open_native_shader_file(path));
        store=std::make_unique<ShaderFileStore>(source,window,plan->input_window_bytes,plan->bytes);
        store->verify(expected);heap_admission();verified.store(true);
    }catch(...){failed.store(true);throw;}
}
const unsigned char*native_shader_file_frame(const void*token,std::size_t bytes,std::size_t original) {
    if(!verified.load()||failed.load()||read_pending.load()||!store||!plan)refuse("External shader input requires its positive current file admission");
    try {
        const auto location=parse_shader_file_location(token,shader_file_token_bytes,bytes,original,plan->bytes);
        const auto*value=store->frame(location.offset,location.bytes);heap_admission();
        if(failed.load())refuse("External shader ownership was quarantined during the completed read");
        ++frame_requests;return value;
    }catch(...){failed.store(true);throw;}
}
NativeShaderFileStats native_shader_file_stats() {
    NativeShaderFileStats s;s.registered=native_shader_file_registered();s.verified=verified.load();s.failed=failed.load();s.read_pending=read_pending.load();
    if(plan)s.file_bytes=plan->bytes;
    s.input_window_bytes=input_bytes.load();s.read_calls=read_calls.load();s.returned_bytes=returned_bytes.load();s.frame_requests=frame_requests.load();return s;
}
}
