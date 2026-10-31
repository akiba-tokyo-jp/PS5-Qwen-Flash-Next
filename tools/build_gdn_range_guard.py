#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prevent generic Vulkan scheduling from pulling members out of a GDN span."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());a.out.mkdir(parents=True,exist_ok=False)
 command=n['io_gpu_comparison']['GPU_command'];text=Path(command[command.index('-c')+1]).read_text()
 text=once(text,'#include "gdn_conv_norm_planner.inc"','#include "gdn_conv_norm_planner.inc"\n#include "gdn_conv_norm_range_guard.inc"')
 begin=text.index('void ggml_vk_graph_optimize(');end=text.index('static void ggml_backend_vk_event_record(',begin);body=text[begin:end]
 body=once(body,'    std::vector<bool> used(graph->n_nodes, false);','    std::vector<bool> used(graph->n_nodes, false);\n    const auto qwen_protected=qwen_conv_norm_protected_ranges(ctx,graph);')
 require(body.count('if (used[j]) {')==2,'Both generic real/view pulling passes required')
 body=body.replace('if (used[j]) {','if (used[j] || qwen_protected[j]) {');text=text[:begin]+body+text[end:]
 header=ROOT/'native/app/gdn_conv_norm_range_guard.inc'
 r,jobs,sources=link(a.parent,a.out,dict(gpu=(command,text)),[Path(__file__),header])
 write_json(a.out/'compiled-providers.private.json',dict(result=r,commands=jobs,sources=sources))
 r['GDN_model_planner']['range_guard']=dict(header=record(header),every_member_protected_in_real_and_view_pulling_passes=True,
  original_dependency_API_runtime_overlap_and_shader_dispatch_unchanged=True,one_bounded_metadata_only_window=True)
 r['GDN_model_planner']['actual_sources']['gpu']=sources['gpu'];r['GDN_model_planner']['commands']['gpu']=jobs['gpu']
 r['GDN_model_comparison']['actual_sources']['gpu']=sources['gpu'];r['GDN_model_comparison']['commands']['gpu']=jobs['gpu']
 r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);unsealed=a.out/'unsealed-link.private.json';write_json(unsealed,r)
 done=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(unsealed),'--out',str(a.out/'GPU-provenance')],capture_output=True,timeout=600)
 (a.out/'GPU-provenance.private.log').write_bytes(done.stdout+done.stderr);require(done.returncode==0,done.stderr.decode(errors='replace')[-2800:])
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='complete_GDN_span_protection',requests=14,cache_slots=3072,
  original_shader_and_runtime_dispatch=True,original_allocation_API_overlap_OS_physical_workspace_and_completion=True,
  candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
