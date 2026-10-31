#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Register the qualified GDN fusion in Vulkan's pre-allocation graph planner."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 old=n['GDN_model_comparison']['scope'];scope=dict(old,Vulkan_graph_optimizer_preserves_potential_spans_in_both_arms=True,
  original_add_alloc_dep_API_keeps_external_inputs_until_last_fused_output=True,original_overlap_rejection_checks_unchanged=True,bounded_metadata_only_planner_counters=True)
 gpu_cmd=n['io_gpu_comparison']['GPU_command'];text=Path(gpu_cmd[gpu_cmd.index('-c')+1]).read_text()
 header=Path(n['GDN_model_comparison']['backend']['path']);original=header.read_text();body=original
 body=once(body,'const ggml_cgraph*graph,int first){','const ggml_cgraph*graph,int first,bool planning=false){')
 body=once(body,'!qwen_conv_norm_enabled.load(std::memory_order_relaxed)||','(!planning&&!qwen_conv_norm_enabled.load(std::memory_order_relaxed))||')
 body=once(body,'if(!program||!program->pipeline||limits.','if((!planning&&(!program||!program->pipeline))||limits.')
 body=once(body,'    QwenConvNormMatch out;','    QwenConvNormMatch out;\n    if(!planning&&qwen_conv_norm_enabled.load(std::memory_order_relaxed)&&graph->nodes[first]->op==GGML_OP_SSM_CONV)++qwen_conv_norm_planner_counts[5];')
 body=once(body,'out.extra=j;out.q=scaled[0];','if(!planning)++qwen_conv_norm_planner_counts[6];out.extra=j;out.q=scaled[0];')
 backend=a.out/'gdn_conv_norm_planner_backend.private.inc';backend.write_text(body,newline='\n')
 text=once(text,'#include "gdn_conv_norm_state.inc"','#include "gdn_conv_norm_state.inc"\n#include "gdn_conv_norm_planner_state.inc"')
 text=once(text,'#include "gdn_conv_norm_model_backend.private.inc"','#include "gdn_conv_norm_planner_backend.private.inc"\n#include "gdn_conv_norm_planner.inc"')
 text=once(text,'        if (keep_topk_moe_pattern(topk_moe_early_softmax_norm)) {',
  '        if(qwen_conv_norm_preserve_plan(ctx,graph,params,new_order,used,used_node_set,first_unused))continue;\n\n        if (keep_topk_moe_pattern(topk_moe_early_softmax_norm)) {')
 text=once(text,'            if (need_disable) {','            if (need_disable) {\n                if(fusion_string&&std::strcmp(fusion_string,"SSM_CONV_SILU_GDN_RMS_SCALE")==0)++qwen_conv_norm_planner_counts[7];')
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include <cstdint>\nextern "C" void qwen_app_conv_norm_planner_stats(std::uint64_t*);\n'+entry
 entry=once(entry,literal(old),literal(scope))
 entry=once(entry,'            row["phase"]=phase;',
  '            std::uint64_t planner_counts[8]{};qwen_app_conv_norm_planner_stats(planner_counts);row["GDN_planner_counters"]=std::vector<std::uint64_t>(planner_counts,planner_counts+8);\n            row["phase"]=phase;')
 headers=[ROOT/'native/app/gdn_conv_norm_planner_state.inc',ROOT/'native/app/gdn_conv_norm_planner.inc']
 r,jobs,sources=link(a.parent,a.out,dict(gpu=(gpu_cmd,text),entry=(ec,entry)),[Path(__file__),header,backend,*headers])
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 for key in('normal_performance','output_Q8_normal','cold_request','resident_all_Q8','resident_cache3072','resident_small_rows','resident_weight_normal','memory_quality_cohort'):
  r[key]['actual_sources']['entry']=sources['entry'];r[key]['commands']['entry']=jobs['entry']
 r['all_Q2_optimized_monitor']['actual_entry']=sources['entry'];r['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];r['routing_winners_normal']['actual_entry']=sources['entry']
 r['GDN_model_comparison'].update(scope=scope,backend=record(backend));r['GDN_model_comparison']['actual_sources'].update(sources);r['GDN_model_comparison']['commands'].update(jobs)
 r['GDN_model_planner']=dict(actual_sources=sources,commands=jobs,headers=[record(h)for h in headers],backend=record(backend),original_backend=record(header),same_numerical_shader_and_runtime_dispatch=True,
  original_allocator_API_and_overlap_guards=True,counter_fields=['optimizer_visits','convolution_visits','matching_spans','allocation_dependencies','preserved_spans','enabled_runtime_probes','enabled_runtime_matches','overlap_rejections'])
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);unsealed=a.out/'unsealed-link.private.json';write_json(unsealed,r)
 result=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600)
 (a.out/'GPU-provenance.private.log').write_bytes(result.stdout+result.stderr);require(result.returncode==0,result.stderr.decode(errors='replace')[-3000:])
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='Vulkan_GDN_planner_comparison',requests=14,original_numeric_shader_and_runtime_dispatch=True,
  original_allocation_dependency_API_and_overlap_checks=True,original_model_driver_physical_OS_minimum_workspace_and_completion=True,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
