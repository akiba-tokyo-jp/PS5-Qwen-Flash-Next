#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare cap12 plus the actually exercised Top2 and two-token GDN kernels."""
import argparse,json,subprocess,sys
from pathlib import Path
from build_cache_capacity_1125 import literal
from build_next_five_comparison import update_sources
from build_speculative_batch_probe import once
from expert_q4 import record,require,write_json
from scoped_native_variant import link,seal
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in('parent','two-token','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();n=json.loads(a.parent.read_text());two=json.loads(a.two_token.read_text());a.out.mkdir(parents=True,exist_ok=False)
 headers=[]
 for row in two['post_top2_two_token']['headers']:
  require(record(row['path'])==row,'Exact qualified GDN2 header required');t=a.out/Path(row['path']).name;t.write_bytes(Path(row['path']).read_bytes());headers.append(t)
 gc=n['io_gpu_comparison']['GPU_command'];gpu=Path(gc[gc.index('-c')+1]).read_text()
 gpu=once(gpu,'#include "gdn_conv_norm_state.inc"','#include "gdn_conv_norm_two_state.private.inc"')
 gpu=once(gpu,'#include "gdn_conv_norm_planner_backend.private.inc"','#include "gdn_conv_norm_two_backend.private.inc"')
 old=n['GDN_model_comparison']['scope'];scope=dict(old,candidate='cap12-Top2-fused-GateUp-two-token-GDN',candidate_attempt_cap=12,control_attempt_cap=6,
  candidate_kernels_require_actual_dispatch=True,common_node_cap=256,additional_shader_registry_capacity=4)
 ec=n['compile_commands'][0];entry=Path(ec[ec.index('-c')+1]).read_text();entry='#include "post_top2_causal.h"\nextern "C" void qwen_app_conv_norm_two_select(bool);\nextern "C" std::uint64_t qwen_app_conv_norm_two_selections();\n'+entry
 entry=once(entry,literal(old),literal(scope));entry=once(entry,'qwen_app_gate_up_trial_select(arm==1);','qwen_app_gate_up_trial_select(arm==1);qwen_app_conv_norm_two_select(arm==1);')
 entry=once(entry,'const auto gate_up_before=qwen_app_gate_up_trial_selections();','const auto two_before=qwen_app_conv_norm_two_selections();const auto gate_up_before=qwen_app_gate_up_trial_selections();')
 entry=once(entry,'qwen_app::NextFiveCausalEngine causal(*engine,model,context,ordinal>=10);','qwen_app::PostTop2CausalEngine causal(*engine,model,context,ordinal>=10,arm?12:6);')
 entry=entry.replace('qwen_app::NextFiveCausalEngine&','qwen_app::PostTop2CausalEngine&')
 entry=once(entry,'            row["phase"]=phase;','            row["two_token_pipeline_selections"]=qwen_app_conv_norm_two_selections()-two_before;\n            if(arm&&row["two_token_pipeline_selections"].get<std::uint64_t>()==0)throw std::runtime_error("C2 requires actual GDN2 execution");\n            row["phase"]=phase;')
 model=n['GDN_model_graph_order'];tm=two['GDN_model_graph_order'];unity=once(Path(model['actual_unity']['path']).read_text(),Path(model['actual_model']['path']).as_posix(),Path(tm['actual_model']['path']).as_posix())
 r,jobs,sources=link(a.parent,a.out,dict(entry=(ec+['-I',str(ROOT/'native/app')],entry),gpu=(gc,gpu),model_graph=(model['command'],unity)),[Path(__file__),a.two_token,Path(tm['actual_model']['path']),ROOT/'native/app/post_top2_causal.h',*headers])
 update_sources(r,jobs,sources);r['io_gpu_comparison'].update(GPU_command=jobs['gpu'],GPU_source=sources['gpu']);r['GDN_model_comparison']['scope']=scope
 r['GDN_model_graph_order'].update(actual_model=tm['actual_model'],actual_unity=sources['model_graph'],object=record(jobs['model_graph'][jobs['model_graph'].index('-o')+1]),command=jobs['model_graph'])
 r['next_five_comparison'].update(scope=scope,actual_sources=sources,commands=jobs);r['post_top2_C2']=dict(scope=scope,actual_sources=sources,commands=jobs,qualified_GDN2_headers=[record(x)for x in headers])
 seed=a.out/'linked-seed.private.json';write_json(seed,r);subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/rebind_gpu_provenance.py'),'--linked',str(seed),'--out',str(a.out/'GPU-provenance')],check=True)
 r=json.loads((a.out/'GPU-provenance/receipt.private.json').read_text());seal(r,a.workspace,a.cache,a.out)
 write_json(a.out/'core-safety.private.json',dict(completed=True,kind='cap12_Top2_GateUp_GDN2_combination',candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
if __name__=='__main__':main()
