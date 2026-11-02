// SPDX-License-Identifier: MIT
#include "gpu_cache_rank_state.h"
#include "ggml.h"
#include <cstdio>
#include <cstring>
#include <mutex>

#ifndef QWEN_GPU_RANK_VALIDATE_SHADOW
#define QWEN_GPU_RANK_VALIDATE_SHADOW 0
#endif
extern "C" void __real_qwen_app_route_begin(unsigned);
extern "C" void __real_qwen_app_route_resident(unsigned,unsigned,bool);
extern "C" void __real_qwen_app_routing_event_begin();
extern "C" void __real_qwen_app_route_rank(ggml_tensor*,const ggml_tensor*,int,int,void*);
extern "C" void __real_qwen_app_route_stats(std::uint64_t*);
extern "C" unsigned qwen_next_variant();
extern "C" void qwen_native_stage(const char*);
namespace {
std::mutex mutex;
qwen_app::GpuCacheRankSnapshot snapshot;
std::uint64_t events=0,CPU_rank_calls=0,CPU_checked_rows=0,GPU_input_publications=0;
std::uint64_t shadow_failures=0,geometry_failures=0,unsupported_variant=0;
}
extern "C" void __wrap_qwen_app_route_begin(unsigned bits){
    std::lock_guard<std::mutex> lock(mutex);__real_qwen_app_route_begin(bits);snapshot.reset();
    events=CPU_rank_calls=CPU_checked_rows=GPU_input_publications=0;
    shadow_failures=geometry_failures=unsupported_variant=0;
}
extern "C" void __wrap_qwen_app_route_resident(unsigned layer,unsigned expert,bool present){
    std::lock_guard<std::mutex> lock(mutex);__real_qwen_app_route_resident(layer,expert,present);snapshot.resident(layer,expert,present);
}
extern "C" void __wrap_qwen_app_routing_event_begin(){
    std::lock_guard<std::mutex> lock(mutex);
    if(qwen_next_variant()!=2)++unsupported_variant;
    __real_qwen_app_routing_event_begin();snapshot.latch();++events;
}
extern "C" void qwen_gpu_cache_rank_coefficients(unsigned layer,float*out,std::size_t count){
    std::lock_guard<std::mutex> lock(mutex);snapshot.coefficients(layer,out,count);++GPU_input_publications;
}
extern "C" void __wrap_qwen_app_route_rank(ggml_tensor*dst,const ggml_tensor*src,int ith,int nth,void*opaque){
    std::lock_guard<std::mutex> lock(mutex);__real_qwen_app_route_rank(dst,src,ith,nth,opaque);++CPU_rank_calls;
    if(QWEN_GPU_RANK_VALIDATE_SHADOW){
        // Diagnostic mismatches never change the original completed result or
        // throw through the CPU worker. The host rejects after ordinary close.
        try{
            std::array<float,512> coefficients{};snapshot.coefficients(unsigned(std::uintptr_t(opaque)),coefficients.data(),coefficients.size());
            const auto count=ggml_nelements(src);const auto*source=static_cast<const float*>(src->data);const auto*target=static_cast<const float*>(dst->data);
            if(src->ne[0]!=512||(src->ne[1]!=1&&src->ne[1]!=2)||src->ne[2]!=1||src->ne[3]!=1)++geometry_failures;
            bool mismatch=count!=512&&count!=1024;
            if(!mismatch){for(std::int64_t i=0;i<count;++i){const float expected=source[i]*coefficients[unsigned(i)%512];
                mismatch|=std::memcmp(&expected,target+i,sizeof(expected))!=0;}CPU_checked_rows+=unsigned(count/512);}
            if(mismatch)++shadow_failures;
        }catch(...){++shadow_failures;}
    }
}
extern "C" void __wrap_qwen_app_route_stats(std::uint64_t*out){
    __real_qwen_app_route_stats(out);char text[320];
    {std::lock_guard<std::mutex> lock(mutex);
        std::snprintf(text,sizeof(text),"G1_rank_scope events=%llu CPU_rank_calls=%llu CPU_checked_rows=%llu GPU_input_publications=%llu shadow_validation=%u shadow_failures=%llu geometry_failures=%llu unsupported_variant=%llu",
            static_cast<unsigned long long>(events),static_cast<unsigned long long>(CPU_rank_calls),
            static_cast<unsigned long long>(CPU_checked_rows),static_cast<unsigned long long>(GPU_input_publications),unsigned(QWEN_GPU_RANK_VALIDATE_SHADOW),
            static_cast<unsigned long long>(shadow_failures),static_cast<unsigned long long>(geometry_failures),static_cast<unsigned long long>(unsupported_variant));}
    qwen_native_stage(text);
}
