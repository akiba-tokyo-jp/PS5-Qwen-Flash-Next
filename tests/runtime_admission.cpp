// SPDX-License-Identifier: MIT
// CPU ownership/failure checks only; no backend, model or GPU implementation.
#include "../native/app/runtime_admission.h"
#include "ggml.h"
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
namespace {
int mode, timed, allocated, freed, phases;
ggml_context context;
void check(bool ok) { if (!ok) throw std::logic_error("CPU runtime ownership check failed"); }
void stage(const char * value) {
    ++phases;
    if (!std::strcmp(value,"CPU_runtime_context_release_completed GPU_not_started=1")) check(freed==1);
    if (!std::strcmp(value,"CPU_runtime_exception_roundtrip_completed GPU_not_started=1")) check(mode==0&&freed==1);
}
}
extern "C" void ggml_time_init() { ++timed; }
extern "C" ggml_context * ggml_init(ggml_init_params p) {
    check(timed==1&&p.mem_size==32768&&p.no_alloc&&!p.mem_buffer);++allocated;return mode==1?nullptr:&context;
}
extern "C" std::size_t ggml_get_mem_size(const ggml_context * c) { check(c==&context);return mode==2?16:32768; }
extern "C" void ggml_free(ggml_context * c) { check(c==&context&&mode==0);++freed; }
int main(int argc,char ** argv) {
    try {
        check(argc==2);mode=std::atoi(argv[1]);bool failed=false;
        try {
            auto result=qwen_app::admit_cpu_runtime(mode==3?nullptr:stage);
            check(mode==0&&result.metadata_bytes==32768&&result.exception_roundtrip);
        } catch (const std::invalid_argument &) { check(mode==3);failed=true; }
          catch (const std::runtime_error &) { check(mode==1||mode==2);failed=true; }
        check(failed==(mode!=0));check(freed==(mode==0?1:0));
        if(mode==3)check(!timed&&!allocated&&!phases);
        std::cout<<"CPU metadata ownership, explicit failures and exception roundtrip checked; API stubs only\n";
    } catch(const std::exception & error) { std::cerr<<error.what()<<'\n';return 1; }
}
