#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare actual compiled physical guards against the completed screen control."""
import argparse, hashlib, json
from pathlib import Path
from audit_expert_all_q2_safety import body
from expert_q4 import record, require, write_json

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('control','candidate','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();control=json.loads(a.control.read_text());candidate=json.loads(a.candidate.read_text())
    old=Path(control['routing_sharing']['actual_sources']['entry']['path']).read_text()
    new=Path(candidate['six_candidate_screen']['actual_sources']['entry']['path']).read_text();checks=[]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget',
                 'model_file_identity','model_directory_identity','resident_reset_empty_context'):
        before,after=body(old,name),body(new,name);require(before==after,'Original physical guard changed: '+name)
        checks.append(dict(function=name,sha256=hashlib.sha256(after.encode()).hexdigest(),unchanged=True))
    for marker in ('qwen_app::require_resident_phase_VM(policy,read_completed_native_report(buffer_proof),true)',
                   'qwen_app::admit_native_system_memory()','qwen_app::enforce_native_model_compute_limits()',
                   'qwen_native_driver_complete()','qwen_app::stop_native_model_sources()',
                   'if(ledger.live||qwen_app_resident_cache_reuse_live_owners())'):
        require(old.count(marker)==new.count(marker)>0,'Original completion boundary changed: '+marker)
        checks.append(dict(call=marker,count=new.count(marker),unchanged=True))
    scope=candidate['six_candidate_screen']['scope']
    require(scope['maximum_requests']==32 and scope['cache_budget_bytes']==1333739520,'Declared bounded scope differs')
    for key in ('cache','engine','capture'):
        require(control['routing_sharing']['actual_sources'][key]==candidate['routing_sharing']['actual_sources'][key],
                'Unchanged cache/engine/capture provider required')
        checks.append(dict(provider=key,unchanged=True))
    for row in candidate['six_candidate_screen']['actual_sources'].values():require(record(row['path'])==row,'Compiled source changed')
    require(candidate['native_dispatch_audit']['passed']and not candidate['real_module_import_audit']['missing'],'Actual dispatch/import gates required')
    write_json(a.out,dict(completed=True,checks=checks,control=record(a.control),candidate=record(a.candidate),
        original_physical_kernel_heap_ledger_ownership_positive_completion_guards_retained=True,PS5_operations=0,CI_runs=0))
    print(json.dumps(dict(guard_families_passed=len(checks),PS5_operations=0)))

if __name__=='__main__':main()
