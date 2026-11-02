// SPDX-License-Identifier: MIT
// CPU-only native-title context for the existing lossless bundle packer.
#pragma once
#include <sys/time.h>
#include <sys/sysctl.h>
namespace {pid_t required_bundle_native_PID=0;std::uint64_t required_bundle_native_device=0;std::string required_bundle_native_anchor;}
static std::array<std::uint64_t,10> required_bundle_source_identity(const std::array<std::uint64_t,10>&original){
    if(original[0]!=REQUIRED_BUNDLE_SOURCE_DEVICE||!required_bundle_native_device)
        throw std::runtime_error("Exact source-to-current-title device translation required");
    auto translated=original;translated[0]=required_bundle_native_device;return translated;
}
extern "C" int split_report_line(const char*line){qwen_native_stage(line);return 1;}
extern "C" int split_open_journal(){return required_bundle_native_PID==getpid();}
extern "C" int split_close_journal(){return required_bundle_native_PID==getpid();}
extern "C" int split_context(unsigned){
    try{
        require_model_CPU_budget();struct timeval boot{};size_t size=sizeof(boot);struct stat root{};
        const int anchor=open(required_bundle_native_anchor.c_str(),O_RDONLY|O_NOFOLLOW);
        if(anchor<0)return 0;
        const bool observed=!fstat(anchor,&root)&&S_ISREG(root.st_mode);
        const bool closed=!close(anchor);
        return observed&&closed&&required_bundle_native_PID==getpid()&&getuid()==1&&
            !sysctlbyname("kern.boottime",&boot,&size,nullptr,0)&&size==sizeof(boot)&&
            boot.tv_sec==REQUIRED_BUNDLE_BOOT_SECONDS&&boot.tv_usec==REQUIRED_BUNDLE_BOOT_MICROSECONDS&&
            required_bundle_native_device&&static_cast<std::uint64_t>(root.st_dev)==required_bundle_native_device;
    }catch(...){return 0;}
}
extern "C" int split_headroom(){try{require_model_CPU_budget();return 1;}catch(...){return 0;}}
extern "C" std::uint64_t split_now_ns(){
    return std::chrono::duration_cast<std::chrono::nanoseconds>(qwen_app::ProfileClock::now().time_since_epoch()).count();
}
