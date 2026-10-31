// SPDX-License-Identifier: MIT
#include <atomic>
#include "additional_shader_assets.h"
#include "qwen_conv_norm_spirv.private.h"
namespace {
struct QwenConvNormPC {uint32_t xo,wo,yo,qo,ko,xstride,wstride;float epsilon,scale;};
static_assert(sizeof(QwenConvNormPC)==36,"Exact convolution-normalization shader ABI");
struct QwenConvNormProgram {vk_device device;vk_pipeline pipeline;};
std::array<std::unique_ptr<QwenConvNormProgram>,8>qwen_conv_norm_programs;
std::mutex qwen_conv_norm_mutex;std::atomic<bool>qwen_conv_norm_enabled{false};
std::atomic<std::uint64_t>qwen_conv_norm_executions{0};
QwenConvNormProgram*qwen_conv_norm_find(const vk_device&device){
    for(auto&v:qwen_conv_norm_programs)if(v&&v->device==device)return v.get();return nullptr;
}
}
static void ggml_app_phase(const char*);
void ggml_vk_destroy_pipeline(vk::Device&,vk_pipeline&);
extern "C" void qwen_app_conv_norm_trial_select(bool enabled){qwen_conv_norm_enabled.store(enabled);}
extern "C" std::uint64_t qwen_app_conv_norm_trial_selections(){return qwen_conv_norm_executions.load();}
extern "C" void qwen_app_conv_norm_trial_release(){
    std::lock_guard<std::mutex>lock(qwen_conv_norm_mutex);qwen_conv_norm_enabled.store(false);
    for(auto&v:qwen_conv_norm_programs)if(v){unsigned count=0;
        for(auto p=v->pipeline;p;p=p->next){if(++count>2||p->compile_pending)throw std::runtime_error("Convolution normalization compilation remains pending");
            if(p->compiled){ggml_vk_destroy_pipeline(v->device->device,p);p->compiled=false;}}
        v.reset();
    }ggml_app_phase("Qwen_convolution_normalization_programs_positively_retired");
}
