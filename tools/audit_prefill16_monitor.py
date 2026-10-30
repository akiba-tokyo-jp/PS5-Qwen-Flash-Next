#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check unchanged physical guards and the exact normal-app width delta."""
import argparse,hashlib,json
from pathlib import Path
from expert_q4 import require,record,write_json
from audit_expert_all_q2_safety import body
from build_prefill16_monitor import engine_source,causal_header_source,ROOT
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('control','candidate','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());checks=[]
 before=Path(old['routing_winners_normal']['actual_entry']['path']).read_text();after=Path(new['routing_winners_normal']['actual_entry']['path']).read_text()
 for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
  x,y=body(before,name),body(after,name)
  if name=='resident_reset_empty_context':x=x.replace('llama_n_batch(context)!=4||','llama_n_batch(context)!=16||')
  require(x==y,'Unexpected physical/identity/reset delta: '+name);checks.append(dict(function=name,original_guard_retained=True,sha256=hashlib.sha256(y.encode()).hexdigest()))
 for marker in ('qwen_app::require_resident_phase_VM(policy,read_completed_native_report(buffer_proof),true)','qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()','qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','if(ledger.live)throw std::runtime_error("Additional model owners remain live")','if(qwen_app_resident_cache_reuse_live_owners())throw std::runtime_error("Original cache reset owner was not retired")'):
  require(before.count(marker)==after.count(marker)>0,'Original positive completion boundary changed');checks.append(dict(call=marker,count=after.count(marker)))
 e0=Path(old['all_Q2_optimized_monitor']['actual_engine']['path']).read_text();e1=Path(new['all_Q2_optimized_monitor']['actual_engine']['path']).read_text()
 require(engine_source(e0)==e1,'Engine changed beyond chosen width validation');checks.append(dict(engine_only_width_validation_changes=True,all_output_logits_retained=True))
 header=new['prefill16_normal']['causal_header'];require(record(header['path'])==header and Path(header['path']).read_text()==causal_header_source((ROOT/'native/app/causal_expert_sharing.h').read_text()),'Causal adapter changed beyond its chosen width validation');checks.append(dict(causal_only_prefill_width_validation_changes=True))
 for key in ('routing','graph'):require(old['routing_sharing']['actual_sources'][key]==new['routing_sharing']['actual_sources'][key],'GPU policy provider changed');checks.append(dict(provider=key,exact_original=True))
 if 'workspace_budget'in new['prefill16_normal']:
  from build_prefill16_workspace_monitor import workspace_header_source
  w=new['prefill16_normal']['workspace_budget'];require(record(w['header']['path'])==w['header']and Path(w['header']['path']).read_text()==workspace_header_source((ROOT/'native/app/device_buffer_budget.h').read_text()),'Workspace header differs beyond its tighter bound')
  require(Path(w['owner_source']['path']).read_bytes()==Path(w['original_owner_source']['path']).read_bytes()and w['aggregate_device_MiB']==1792 and w['CPU_MiB']==512,'Source reader or total working budget changed')
  linked=Path(new['artifact']['path']).with_name('native-link.private.map').read_text();require(str(Path(w['owner_object']['path']))+':(.text.qwen_app_model_workspace_admit)'in linked,'Actual workspace callback must use the new owner object')
  checks.append(dict(workspace_bound_tightened_MiB=248,original_total_device_MiB=1792,CPU_MiB=512))
 for row in new['prefill16_normal']['actual_sources'].values():require(record(row['path'])==row,'Actual compiled source changed')
 require(new['prefill16_normal']['scope']['prefill_tokens']==16 and new['prefill16_normal']['scope']['all_prompt_outputs_requested']and new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Exact scope, imports and native dispatch required')
 write_json(a.out,dict(completed=True,checks=checks,original_physical_kernel_heap_ledger_ownership_positive_completion_guards_retained=True,chosen_width_policy=dict(previous=4,selected=16),PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(completed=True,guard_families=len(checks),PS5_operations=0)))
if __name__=='__main__':main()
