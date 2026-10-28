// SPDX-License-Identifier: MIT
#include "bounded_gpu_profile.h"
#include <cassert>
bool vk_perf_logger_enabled=false,vk_perf_logger_concurrent=false;
std::uint32_t vk_perf_logger_frequency=0;
int main(){
    qwen_app::BoundedGpuProfile profile;profile.start();
    std::cerr<<"----------------\nVulkan Timings:\nMUL_MAT bf16 [2560,640]: 2 x 15 us = 30 us (1 GFLOPS/s)\n";
    std::cerr<<"Vulkan Timings:\nMUL_MAT bf16 [2560,640]: 1 x 14 us = 14 us\n";
    auto result=profile.finish();assert(result.at("complete").get<bool>());
    assert(result.at("blocks")==2&&result.at("rows").size()==1);
    assert(result.at("rows").at(0).at("calls")==3);
    assert(result.at("rows").at(0).at("GPU_microseconds")==44);
    assert(!vk_perf_logger_enabled);
}
