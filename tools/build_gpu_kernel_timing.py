#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use existing Vulkan timestamp instrumentation with bounded waits and counters."""
import argparse,json,shlex
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import require,record
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
GROUPS=['Q2_weight_conversion','Q2_MoE_matmul','output_projection','shared_Expert_matmul','attention_SSM','other']
GPU_COUNTERS=r'''
#include <array>
#include <cmath>
namespace {std::array<std::uint64_t,14>qwen_GPU_timing{};
void qwen_GPU_node(const ggml_tensor*n,std::uint64_t before,std::uint64_t after,double period){
 const auto bits=qwen_GPU_timing[12];const auto mask=bits==64?UINT64_MAX:(std::uint64_t(1)<<bits)-1;
 const auto ns=std::uint64_t(double((after-before)&mask)*period);
 if(!bits||ns>60000000000ull)throw std::runtime_error("GPU timestamp interval exceeds the bounded diagnostic");
 const auto*w=n&&n->src[0]?n->src[0]:nullptr;const char*weight=w?w->name:"",*name=n?n->name:"";
 const bool Q2=w&&(w->type==GGML_TYPE_Q2_0||w->type==GGML_TYPE_Q2_K);
 const bool matrix=n&&(n->op==GGML_OP_MUL_MAT||n->op==GGML_OP_MUL_MAT_ID);
 unsigned group=5;
 if(Q2)group=matrix?1:0;
 else if(std::strstr(weight,"output.weight")||std::strstr(name,"result_output"))group=2;
 else if(matrix&&(std::strstr(weight,"shexp")||std::strstr(name,"shared")))group=3;
 else if(std::strstr(weight,"attn")||std::strstr(weight,"ssm")||std::strstr(name,"attn")||std::strstr(name,"ssm")||std::strstr(name,"delta"))group=4;
 qwen_GPU_timing[group]+=ns;++qwen_GPU_timing[6+group];
}}
extern "C" void qwen_app_GPU_kernel_timing(std::uint64_t*out){
 if(!out)throw std::runtime_error("Missing GPU timing target");std::copy(qwen_GPU_timing.begin(),qwen_GPU_timing.end(),out);
}
'''
def gpu_source(text):
    text=once(text,'#include "ggml-vulkan-common.h"','#include "ggml-vulkan-common.h"\n'+GPU_COUNTERS)
    text=once(text,'vk_perf_logger_concurrent = getenv("GGML_VK_PERF_LOGGER_CONCURRENT") != nullptr;','vk_perf_logger_concurrent = false; // Isolated per-operation timestamp diagnostic.')
    text=once(text,'        ctx->perf_logger = std::unique_ptr<vk_perf_logger>(new vk_perf_logger());',
        '''        const auto families=ctx->device->physical_device.getQueueFamilyProperties();
        const auto family=ctx->device->compute_queue->queue_family_index;
        if(family>=families.size()||!families[family].timestampValidBits||families[family].timestampValidBits>64||
           !std::isfinite(ctx->device->properties.limits.timestampPeriod)||ctx->device->properties.limits.timestampPeriod<=0)
            throw std::runtime_error("Physical compute queue does not support valid timestamps");
        qwen_GPU_timing[12]=families[family].timestampValidBits;
        qwen_GPU_timing[13]=std::uint64_t(ctx->device->properties.limits.timestampPeriod*1000.0);
        ctx->perf_logger = std::unique_ptr<vk_perf_logger>(new vk_perf_logger());''')
    text=once(text,'ctx->device->device.waitForFences({ ctx->device->fence }, true, UINT64_MAX), "GGML_VULKAN_PERF waitForFences"',
        'ctx->device->device.waitForFences({ ctx->device->fence }, true, 5000000000ULL), "GGML_VULKAN_PERF waitForFences"')
    text=once(text,'vk::QueryResultFlagBits::e64 | vk::QueryResultFlagBits::eWait), "get timestamp results"','vk::QueryResultFlagBits::e64), "get timestamp results"')
    return once(text,'ctx->perf_logger->log_timing(node, name, uint64_t((timestamps[i] - timestamps[i-1]) * ctx->device->properties.limits.timestampPeriod));',
        'qwen_GPU_node(node,timestamps[i-1],timestamps[i],ctx->device->properties.limits.timestampPeriod);')
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
    manifest_path=Path(prior['bounded_model_source_manifest']['path']);manifest=json.loads(manifest_path.read_text())
    original=next(x for x in manifest['objects']if x['source'].endswith('ggml-vulkan.cpp'))
    require(original['object']==prior['lossless_shader_storage']['vulkan_object'],'Exact selected Vulkan application provider required')
    gpu_command=shlex.split(original['command'],posix=False)if isinstance(original['command'],str)else original['command'].copy()
    gpu_command=[x[1:-1]if x.startswith('"')and x.endswith('"')else x for x in gpu_command]
    gpu_path=Path(gpu_command[gpu_command.index('-c')+1]);require(record(original['object']['path'])==original['object'],'Original Vulkan object changed')
    cmd=prior['compile_commands'][0];entry=Path(cmd[cmd.index('-c')+1]).read_text()
    entry='#include <cstdint>\nextern "C" void qwen_app_GPU_kernel_timing(std::uint64_t*);\nnamespace {std::uint64_t qwen_GPU_prefill_end[14]{};}\nvoid qwen_GPU_mark_prefill(){qwen_app_GPU_kernel_timing(qwen_GPU_prefill_end);}\n'+entry
    at=entry.index('    try {',entry.index('int main(int argc, char ** argv) {'))+len('    try {')
    entry=entry[:at]+'\n        if(setenv("GGML_VK_PERF_LOGGER","1",1)||setenv("GGML_VK_PERF_LOGGER_FREQUENCY","1000000",1))throw std::runtime_error("GPU timestamp diagnostic environment failed");\n'+entry[at:]
    entry=once(entry,'            const auto perf=performance_snapshot(*engine);','            std::uint64_t GPU_before[14]{};qwen_app_GPU_kernel_timing(GPU_before);\n            const auto perf=performance_snapshot(*engine);')
    entry=once(entry,'causal.prefill(n);base=e.checkpoint_validation_stats();','causal.prefill(n);qwen_GPU_mark_prefill();base=e.checkpoint_validation_stats();')
    marker='            row["actual_graph_reuses"]='
    entry=once(entry,marker,'            std::uint64_t GPU_after[14]{};qwen_app_GPU_kernel_timing(GPU_after);Json GPU_groups=Json::array();\n            const char*GPU_names[]={'+','.join(json.dumps(g)for g in GROUPS)+'};\n            for(unsigned g=0;g<6;++g)GPU_groups.push_back({{"group",GPU_names[g]},{"kernel_ns",GPU_after[g]-GPU_before[g]},{"prefill_kernel_ns",qwen_GPU_prefill_end[g]-GPU_before[g]},{"decode_kernel_ns",GPU_after[g]-qwen_GPU_prefill_end[g]},{"intervals",GPU_after[6+g]-GPU_before[6+g]}});\n            row["GPU_kernel_timing"]={{"groups",GPU_groups},{"timestamp_valid_bits",GPU_after[12]},{"timestamp_period_ps",GPU_after[13]},\n                {"diagnostic_scheduling_changes",true},{"ordinary_speed_comparison_valid",false},{"host_source_wait_and_external_copies_excluded",true},{"fused_ranges_attributed_to_terminal_node",true}};\n'+marker)
    entry=once(entry,'{"GPU_timestamp_queries", false}','{"GPU_timestamp_queries", true}')
    entry=once(entry,'{"GPU_operations_added", false}','{"GPU_operations_added", true}')
    result,commands,sources=link(a.parent,a.out,{'entry':(cmd,entry),'GPU':(gpu_command,gpu_source(gpu_path.read_text()))},
        [Path(__file__),manifest_path,gpu_path,Path(original['object']['path'])])
    for key in ('normal_performance','output_Q8_normal'):
        result[key]['actual_sources'].update(sources);result[key]['commands'].update(commands)
    result['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];result['routing_winners_normal']['actual_entry']=sources['entry']
    result['GPU_kernel_timing']=dict(actual_sources=sources,commands=commands,original_GPU_source=record(gpu_path),original_GPU_object=original['object'],groups=GROUPS,
        existing_shader_math_unchanged=True,selected_driver_unchanged=True,additional_GPU_timestamp_operations=True,
        per_graph_fence_timeout_ns=5000000000,query_result_WAIT_flag=False,diagnostic_only=True,ordinary_speed_comparison_valid=False)
    seal(result,a.workspace,a.cache,a.out);print('Bounded Vulkan kernel timestamp diagnostic built; its timing overhead is not an ordinary speed comparison.')
if __name__=='__main__':main()
