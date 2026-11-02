#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Admit returned Direct capacity after a source-bound ordinary title exit."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from kernel_vm_preflight import query
from start_success_route import load,need,save
from success_case_control import current_files,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','prior-close','case','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=load(a.prior_close);result=load(a.case/'result.private.json')
    plan=load(a.case/'case/plan.private.json');first=load(a.case/'case/native-first-start.private.json')
    package=load(plan['package']['path']);profile_record=package['effective_application_policy']['profile']
    need(record(profile_record['path'])==profile_record,'The compiled CPU query profile changed')
    profile=load(profile_record['path']);scope=profile['overrides']['native_headless_model_audit']
    need(result['completed'] and result['kind']=='CPU-Direct-readmission' and result['native_requests']==0 and
         result['native_owners']==0 and not result['unknown_completion'] and
         scope['early_return_before_model_source_initialization'] and
         scope['prior_close']==record(a.prior_close)['sha256'] and
         profile['unloaded_CPU_fixture'] and scope['GPU_calls']==scope['source_workers_created']==0,
         'The exact early CPU query must complete and close ordinarily')
    for key in ('terminal','audit','closure'):need(record(result[key]['path'])==result[key],'A completed query receipt changed')
    audit=load(result['audit']['path']);terminal=load(result['terminal']['path']);closed=load(result['closure']['path'])
    need(terminal['audit']==audit and all(audit[key]==value for key,value in
         (('completed',True),('model_loads',0),('GPU_calls',0),('model_sources_initialized',False),
          ('source_workers_created',0),('source_payload_reads',0),('device_ledger_initialized',False),('CPU_libc_fallbacks',0))) and
         audit['pid']==first['pid']==terminal['pid'] and audit['run_id']==plan['run_id']==first['run_id'] and
         audit['candidate_SELF_sha256']==plan['SELF']['sha256']==terminal['candidate_SELF_sha256'],
         'An exact native-bound CPU-only query without fallback allocations is required')
    minimum=prior['required_title_context_Direct_baseline']
    need(audit['Direct_pool_bytes']==12280922112 and audit['Direct_query_valid'] and audit['query_rc']==0 and
         audit['required_pre_model_available']==scope['required_Direct_available']==minimum and
         audit['Direct_readmission_passed'] and audit['largest_Direct_available']>=minimum and
         audit['largest_start']>=0 and audit['largest_start']+audit['largest_Direct_available']<=audit['Direct_pool_bytes'],
         'The title-context Direct query must recover the complete prior pre-model capacity')
    need(closed['completed'] and closed['ordinary_OS_closes']==1 and closed['ordinary_exit_observed'] and
         closed['current_seven_restored_and_native_hashed'] and current_files(a.current)==plan['old_files'],
         'Positive ordinary exit and exact current restoration are required')
    state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['GPU_retirement_readmission_pending'] and state['GPU_retirement_readmission_proof']==record(a.prior_close) and
         state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Only the same pending known-completed GPU retirement may be admitted')
    a.out.mkdir(parents=True,exist_ok=False);lan=lan_module();vm_dir=a.out/'VM';vm_dir.mkdir();vm=query(lan.HOST,vm_dir)
    need(vm['boot_before']==vm['boot_after']==state['current_boot'],'The same console boot is required')
    with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
        need(not any(row['name']=='eboot.bin' for row in json.loads(response.read())['processes']),'No title owner may remain')
    proof=dict(completed=True,prior_close=record(a.prior_close),CPU_query_case=record(a.case/'result.private.json'),
        native_audit=result['audit'],ordinary_close=result['closure'],current_boot=state['current_boot'],
        prior_pre_model_Direct_available=minimum,observed_title_Direct_available=audit['largest_Direct_available'],
        Direct_capacity_readmitted=True,GPU_calls=0,initializer_requests=0,native_owners=0,automatic_retries=0,
        original_model_numerics_requalified=False,production_adopted=False)
    save(a.out/'result.private.json',proof)
    state.update(GPU_retirement_readmission_pending=False,GPU_retirement_readmission_complete=record(a.out/'result.private.json'),
        state='known_completed_GPU_work_ordinarily_closed_Direct_capacity_readmitted_current_restored')
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=True,Direct_capacity_readmitted=True,available=audit['largest_Direct_available'],GPU_calls=0,native_owners=0)))


if __name__=='__main__':main()
