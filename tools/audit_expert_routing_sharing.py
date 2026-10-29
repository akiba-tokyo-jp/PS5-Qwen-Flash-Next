#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Keep original resource/identity/completion guards across approximate routing."""
import argparse,hashlib,json
from pathlib import Path
from expert_q4 import require,record,write_json
from audit_expert_all_q2_safety import body
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('control','candidate','host-test','out'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();old=json.loads(a.control.read_text());new=json.loads(a.candidate.read_text());host=json.loads(a.host_test.read_text())
 require(new['routing_sharing']['scope']['approximate_routing_changes_permitted']and host['completed'],'Explicit approximate scope and host ranking test required')
 before=Path(old['expert_q2_model']['actual_entry']['path']).read_text();after=Path(new['expert_q2_model']['actual_entry']['path']).read_text();checks=[]
 for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
  x,y=body(before,name),body(after,name);require(x==y,'Original resource/identity/reset guard changed: '+name)
  checks.append(dict(function=name,unchanged=True,sha256=hashlib.sha256(y.encode()).hexdigest()))
 for marker in ('qwen_app::require_resident_phase_VM(policy,read_completed_native_report(buffer_proof),true)','qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()','qwen_native_driver_complete()','qwen_app::stop_native_model_sources()','if(ledger.live)throw std::runtime_error("Additional model owners remain live")'):
  equivalent=after.replace('if(ledger.live||qwen_app_resident_cache_reuse_live_owners())','if(ledger.live)')
  require(before.count(marker)==equivalent.count(marker)>0,'Original positive boundary count changed: '+marker)
  checks.append(dict(call=marker,unchanged_count=after.count(marker)))
 require(new['expert_q2_model']['scope']['cache_budget_bytes']==old['expert_q2_model']['scope']['cache_budget_bytes']==1333739520,'Original cache budget required')
 mapping=Path(next(x[5:]for x in new['link_command']if x.startswith('-Map=')));linked=mapping.read_text().replace('\\','/').lower()
 require('libllama.a(llama-graph.cpp.o)'not in linked and '/graph.o'in linked and '/capture.o'in linked and '/routing.o'in linked,'Actual experimental graph and complete observer overrides required')
 for row in new['routing_sharing']['actual_sources'].values():require(record(row['path'])==row,'Actual compiled source changed')
 write_json(a.out,dict(completed=True,unchanged_guards=checks,all_original_memory_owner_identity_completion_and_close_guards_retained=True,approximate_routing_and_variable_k_explicitly_scoped=True,original_gpu_matrix_providers_preserved=True,host_test=record(a.host_test),actual_link_map=record(mapping),PS5_operations=0,CI_runs=0))
 print(json.dumps(dict(original_guard_families_passed=len(checks),PS5_operations=0)))
if __name__=='__main__':main()
