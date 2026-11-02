#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Record the completed ordinary exit/restoration while a title-context Direct query remains required."""
import argparse
import json
from pathlib import Path

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import current_files,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','case-plan','closure','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();case=load(a.case_plan);source=load(a.closure/'source-audit.private.json')
    close=load(a.closure/'ordinary-close/result.private.json');restore=load(a.closure/'restore/result.private.json');query=load(a.closure/'Direct-after-exit/result.private.json')
    need(close['completed'] and close['operation_calls']==1 and close['helper_exited'] and close['helper_files_removed'] and
         restore['completed'] and restore['operation_calls']==3 and restore['helper_exited'] and restore['helper_files_removed'] and
         query['completed'] is False and query['operation_calls']==0 and query['helper_exited'] and query['helper_files_removed'],
         'Exact completed ordinary close, restoration and returned zero-operation query required')
    raw=Path(query['raw']['path']).read_bytes();need(record(query['raw']['path'])==query['raw'] and
        b'DIRECT_POOL total=0 query_rc=-1 largest_start=-1 largest_available=0 query_only=1' in raw and b'no_native_owner=1' in raw,
        'Only the outside-title Direct query limitation is admitted')
    need(source['completed'] and source['proof']['all_GPU_epochs_positively_completed']==5 and
        source['proof']['target_prefill_GPU_calls']==source['proof']['auxiliary_contexts_created']==0 and
        current_files(a.current)==case['old_files'],'The source-bound completed GPU work and selected deployment must remain exact')
    lan=lan_module()
    with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
        need(not any(row['name']=='eboot.bin' for row in json.loads(response.read())['processes']),'No native title may remain')
    state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['active_successful_native_case']['run_id']==case['run_id'],'Exact source-bound case required')
    a.out.mkdir(parents=True,exist_ok=False)
    result=dict(completed=True,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,native_owners=0,
        GPU_work_completion_known=True,Direct_retirement_readmission_pending=True,
        required_title_context_Direct_baseline=source['Direct_pre_model_available_baseline'],
        source_audit=record(a.closure/'source-audit.private.json'),ordinary_close=record(a.closure/'ordinary-close/result.private.json'),
        restoration=record(a.closure/'restore/result.private.json'),outside_title_query=record(a.closure/'Direct-after-exit/result.private.json'),
        initializer_requests=0,GPU_reset_calls=0,automatic_retries=0)
    save(a.out/'result.private.json',result)
    state.update(state='S1_known_completed_GPU_work_ordinarily_closed_current_restored_Direct_readmission_pending',
        native_running=False,model_loaded=False,native_owners=0,gateway_running=False,original_restored=True,unknown_completion=False,
        current_boot_Qwen_model_admitted=False,current_boot_readmission_pending=True,GPU_retirement_readmission_pending=True,
        GPU_retirement_readmission_proof=record(a.out/'result.private.json'))
    state.pop('temporary_installed_SELF',None);state['active_successful_native_case']['phase']='ordinarily-closed-current-restored-title-Direct-query-pending'
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=True,native_owners=0,current_restored=True,GPU_work_completion_known=True,Direct_readmission_pending=True)))


if __name__=='__main__':main()
