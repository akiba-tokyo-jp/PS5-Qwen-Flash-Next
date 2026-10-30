#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fit prefill32 checkpoints by tightening workspace, never increasing a cap."""
import argparse,json
from pathlib import Path
from build_speculative_batch_probe import once
from build_cache_capacity_1125 import literal
from expert_q4 import require,record,write_json
from scoped_native_variant import link,seal
from audit_expert_all_q2_safety import body

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('parent','workspace','cache','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());require(prior['cold_request']['scope']['mode']=='prefill32','Exact width32 parent required');a.out.mkdir(parents=True,exist_ok=False)
    commands=dict(entry=prior['compile_commands'][0],owner=prior['all_Q2_optimized_monitor']['commands'][1]);sources={k:Path(c[c.index('-c')+1]).read_text()for k,c in commands.items()}
    owner_dir=Path(commands['owner'][commands['owner'].index('-c')+1]).parent
    header_parent=owner_dir/'device_buffer_budget.h'
    if not header_parent.exists():
        candidates=[Path(x[i+1])/'device_buffer_budget.h'for x in [commands['owner']]for i,v in enumerate(x[:-1])if v=='-I'and(Path(x[i+1])/'device_buffer_budget.h').exists()]
        header_parent=candidates[0]
    header=a.out/'device_buffer_budget.h';header.write_text(once(header_parent.read_text(),'model_internal_workspace_budget = 64ull << 20','model_internal_workspace_budget = 48ull << 20'),newline='\n')
    entry=once(sources['entry'],'memory_budget.workspace=64ull<<20;','memory_budget.workspace=48ull<<20;')
    scope=dict(prior['cold_request']['scope'],mode='prefill32_workspace48',workspace_limit_bytes=48<<20,physical_reserves_unchanged=True,device_ledger_cap_increased=False)
    entry=once(entry,literal(prior['cold_request']['scope']),literal(scope))
    updated=[]
    for original in (prior['all_Q2_optimized_monitor']['scope'],prior['expert_q2_model']['scope'],prior['output_Q8_normal']['probation_scope']):
        new=dict(original)
        if 'workspace_budget_bytes'in new:new['workspace_budget_bytes']=48<<20;entry=once(entry,literal(original),literal(new))
        updated.append(new)
    entry=once(entry,'            row["cold_request_timing"]=',
        '            row["actual_workspace_capacity_peak_bytes"]=qwen_app_workspace_actual_peak();row["workspace_reservation_bytes"]=48ull<<20;\n            row["cold_request_timing"]=')
    # Retain canonical unchanged headers. Copying pragma-once headers can make
    # quoted and angle includes select two distinct files in one translation unit.
    parent_headers=[]
    for name in ('completed_expert_routes.h','causal_expert_sharing.h','prefill16_policy.h'):
        old=Path(commands['entry'][commands['entry'].index('-c')+1]).parent/name
        require(old.exists(),'Explicit width32 local header required');parent_headers.append(old)
    sources['entry']=entry
    result,jobs,actual=link(a.parent,a.out,{k:(commands[k],v)for k,v in sources.items()},[Path(__file__),header_parent,*parent_headers,*a.out.glob('*.h')])
    normal,model,probation=updated
    for key in ('normal_performance','output_Q8_normal','routing_sharing','routing_winners_normal'):
        result[key].update(scope=normal,model_scope=model)
        if 'actual_sources'in result[key]:result[key]['actual_sources'].update(actual)
        if 'commands'in result[key]and isinstance(result[key]['commands'],dict):result[key]['commands'].update(jobs)
    result['output_Q8_normal']['probation_scope']=probation;result['expert_q2_model']['scope']=model
    result['all_Q2_optimized_monitor'].update(scope=normal,actual_entry=actual['entry']);result['all_Q2_optimized_monitor']['commands'][0]=jobs['entry'];result['routing_winners_normal']['actual_entry']=actual['entry']
    checks=[]
    for name in ('observed_system_headroom','require_model_CPU_budget','wait_for_initial_model_CPU_budget','model_file_identity','model_directory_identity','resident_reset_empty_context'):
        require(body(sources['entry'],name)==body(Path(commands['entry'][commands['entry'].index('-c')+1]).read_text(),name),'Original guard changed');checks.append(name)
    result['cold_request']=dict(scope=scope,actual_sources=actual,commands=jobs,guard_checks=checks,normal_validation_pending=True,production_adopted=False,
        previous_workspace_bytes=64<<20,workspace_bytes=48<<20,actual_capacity_checked_on_every_callback=True,original_driver_physical_kernel_heap_ledger_completion_guards=True,
        tightened_workspace_header=record(header),device_ledger_cap_bytes=2480332800,physical_memory_reclaimed_claimed=False)
    seal(result,a.workspace,a.cache,a.out)
    write_json(a.out/'core-safety.private.json',dict(completed=True,kind='tightened_workspace_guard_audit',driver_and_original_physical_reserves_preserved=True,unchanged_guard_functions=checks,candidate=record(a.out/'receipt.private.json'),PS5_operations=0,CI_runs=0))
    print(json.dumps(dict(built=True,prefill=32,workspace_MiB=48,device_cap_increased=False)))
if __name__=='__main__':main()
