# SPDX-License-Identifier: MIT
"""Add the qualified F32 convolution/SiLU/RMS-plus-scale graph fusion."""
from build_speculative_batch_probe import once
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CREATE=r'''
    {
        std::lock_guard<std::mutex>lock(qwen_conv_norm_mutex);auto*program=qwen_conv_norm_find(device);
        if(!program){auto free=std::find_if(qwen_conv_norm_programs.begin(),qwen_conv_norm_programs.end(),[](const auto&v){return !v;});
            if(free==qwen_conv_norm_programs.end())throw std::runtime_error("Bounded convolution normalization device registry exhausted");
            *free=std::make_unique<QwenConvNormProgram>();program=free->get();program->device=device;
        }
        ggml_vk_create_pipeline(device,program->pipeline,"qwen_conv_norm_f32",sizeof(qwen_conv_norm_spirv),
            reinterpret_cast<const unsigned char*>(qwen_conv_norm_spirv),"main",5,sizeof(QwenConvNormPC),{128,1,1},{},1);
    }
'''
def transform(text):
 text=once(text,'#include "ggml-vulkan-common.h"','#include "ggml-vulkan-common.h"\n#include "gdn_conv_norm_state.inc"')
 marker='    ggml_vk_create_pipeline(device, device->pipeline_ssm_conv_bias_silu_f32,'
 start=text.index(marker);end=text.index('\n',start)+1;text=text[:end]+CREATE+text[end:]
 text=once(text,'void ggml_vk_ssm_conv(ggml_backend_vk_context * ctx, vk_context& subctx, const struct ggml_cgraph * cgraph, int node_idx) {',
     '#include "gdn_conv_norm_backend.inc"\nvoid ggml_vk_ssm_conv(ggml_backend_vk_context * ctx, vk_context& subctx, const struct ggml_cgraph * cgraph, int node_idx) {\n    if(ctx->num_additional_fused_ops>=7){const auto match=qwen_conv_norm_match(ctx,cgraph,node_idx);GGML_ASSERT(match.extra==int(ctx->num_additional_fused_ops));qwen_conv_norm_dispatch(ctx,subctx,cgraph,node_idx,match);return;}')
 text=once(text,'            if (num_adds) {',
     '            const auto qwen_norm=qwen_conv_norm_match(ctx,cgraph,i);\n            if(qwen_norm.extra){ctx->num_additional_fused_ops=qwen_norm.extra;ctx->fused_ops_write_mask=qwen_norm.writes;fusion_string="SSM_CONV_SILU_GDN_RMS_SCALE";\n                for(int j=0;j<=qwen_norm.extra;++j)op_srcs_fused_elementwise[j]=j!=0&&cgraph->nodes[i+j]->op!=GGML_OP_RMS_NORM;\n            }else if (num_adds) {')
 text=once(text,'            // There are up to two output nodes - topk_moe has two.','            // The GDN normalization fusion has three physical output nodes.')
 text=once(text,'            ggml_tensor *output_nodes[2] {};','            ggml_tensor *output_nodes[3] {};')
 old='''            if (bits) {
                int output_idx = find_first_set(bits);
                GGML_ASSERT(bits == (1u << output_idx));
                output_nodes[1] = cgraph->nodes[i + output_idx];
            }'''
 new='''            for(unsigned output=1;bits;++output){
                GGML_ASSERT(output<3);const int output_idx=find_first_set(bits);bits&=~(1u<<output_idx);
                output_nodes[output]=cgraph->nodes[i+output_idx];
            }'''
 text=once(text,old,new);text=once(text,'            for (int j = 0; j < 2; ++j) {\n                ggml_tensor *dst = output_nodes[j];',
     '            for (int j = 0; j < 3; ++j) {\n                ggml_tensor *dst = output_nodes[j];')
 return text
