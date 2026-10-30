#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify the sole context-capacity policy change and unchanged physical guards."""
import argparse,hashlib,json
from pathlib import Path
from expert_q4 import require,record,write_json
from audit_expert_all_q2_safety import body

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('control','candidate','host-test','out'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());host=json.loads(a.host_test.read_text())
 require(host['completed']and new['lean_prefill']['scope']['prefill_widths']==[4,8,16],'Explicit finite width scope and host boundary checks required')
 before=Path(old['routing_sharing']['actual_sources']['entry']['path']).read_text();after=Path(new['lean_prefill']['actual_sources']['entry']['path']).read_text();checks=[]
 for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
  x,y=body(before,name),body(after,name)
  if name=='resident_reset_empty_context':
   require(x.count('llama_n_batch(context)!=4||')==1,'One original chosen context-width policy required')
   x=x.replace('llama_n_batch(context)!=4||','llama_n_batch(context)!=16||')
  require(x==y,'Physical/owner/identity/reset guard differs beyond the declared context width: '+name)
  checks.append(dict(function=name,unchanged_except_declared_context_capacity=True,sha256=hashlib.sha256(y.encode()).hexdigest()))
 for marker in ('qwen_app::require_resident_phase_VM(policy,read_completed_native_report(buffer_proof),true)','qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()','qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','if(ledger.live||qwen_app_resident_cache_reuse_live_owners())'):
  require(before.count(marker)==after.count(marker)>0,'Original positive completion/resource boundary count differs')
  checks.append(dict(call=marker,unchanged_count=after.count(marker)))
 require(new['lean_prefill']['scope']['cache_budget_bytes']==1333739520,'Original cache byte limit required')
 for row in new['lean_prefill']['actual_sources'].values():require(record(row['path'])==row,'Actual compiled source changed')
 if 'CPU_miss_bookkeeping_capacity'in new['lean_prefill']:
  from build_lean_prefill_cache_capacity import cache_source
  old_cache=Path(old['routing_sharing']['actual_sources']['cache']['path']).read_text()
  new_cache=Path(new['routing_sharing']['actual_sources']['cache']['path']).read_text()
  require(cache_source(old_cache)==new_cache,'Cache changed beyond two bounded CPU metadata arrays')
  checks.append(dict(cache_CPU_bookkeeping=160,original_physical_IO_and_GPU_code_unchanged=True,additional_stack_bytes=1080))
 require(new['native_dispatch_audit']['passed']and not new['real_module_import_audit']['missing'],'Actual physical dispatch and real imports required')
 write_json(a.out,dict(completed=True,checks=checks,chosen_context_capacity_change=dict(previous=4,candidate=16),
  original_physical_kernel_heap_ledger_ownership_positive_completion_guards_retained=True,
  host_test=record(a.host_test),PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(guard_families_passed=len(checks),declared_context_capacity=16,PS5_operations=0)))
if __name__=='__main__':main()
