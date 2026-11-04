// SPDX-License-Identifier: MIT
// Qualification only: hash the existing CPU rows after the original observer.
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <utility>
extern "C" {
#include "hash/sha256/sha256.h"
}
#ifndef QWEN_F32_OBSERVER_SETTER
#error The actual retained engine setter symbol must be supplied
#endif
#ifndef QWEN_F32_OBSERVER_COLUMNS
#error The authenticated current model vocabulary must be supplied
#endif
namespace qwen_app {class LlamaEngine;}
using Observer=std::function<void(const float*,std::size_t)>;
extern "C" void qwen_native_stage(const char*);
extern "C" void qwen_f32_real_setter(qwen_app::LlamaEngine*,Observer)
    __asm__("__real_" QWEN_F32_OBSERVER_SETTER);
extern "C" void qwen_f32_wrap_setter(qwen_app::LlamaEngine*,Observer)
    __asm__("__wrap_" QWEN_F32_OBSERVER_SETTER);
namespace {
// The selected application has one synchronous model producer and one engine.
std::uint64_t request=0,rows=0,failures=0;
void completed_row(const float*values,std::size_t count)noexcept{
    ++rows;
    if(!values||count!=QWEN_F32_OBSERVER_COLUMNS||rows>33){++failures;return;}
    sha256_t hash;unsigned char digest[32];char hex[65],text[200];
    sha256_init(&hash);
    sha256_update(&hash,reinterpret_cast<const unsigned char*>(values),count*sizeof(float));
    sha256_final(&hash,digest);
    for(unsigned i=0;i<32;++i){hex[2*i]="0123456789abcdef"[digest[i]>>4];hex[2*i+1]="0123456789abcdef"[digest[i]&15];}
    hex[64]=0;
    std::snprintf(text,sizeof(text),"F32_row request=%llu row=%llu columns=%zu sha256=%s",
        static_cast<unsigned long long>(request),static_cast<unsigned long long>(rows),count,hex);
    qwen_native_stage(text);
}
}
extern "C" void qwen_f32_wrap_setter(qwen_app::LlamaEngine*engine,Observer observer){
    if(!observer){
        qwen_f32_real_setter(engine,{});
        char text[160];std::snprintf(text,sizeof(text),"F32_request_completed request=%llu rows=%llu failures=%llu",
            static_cast<unsigned long long>(request),static_cast<unsigned long long>(rows),static_cast<unsigned long long>(failures));
        qwen_native_stage(text);return;
    }
    ++request;rows=failures=0;
    qwen_f32_real_setter(engine,[original=std::move(observer)](const float*values,std::size_t count){
        original(values,count);completed_row(values,count);
    });
}
