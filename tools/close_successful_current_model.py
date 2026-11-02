#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ordinarily close a positively retired current model and restore selected files."""
import argparse
import json
from pathlib import Path
import time
import urllib.parse

from build_performance_quantizer import record
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();case=load(args.case_plan);observer=args.case_plan.parent/'passive-observer'
    completed=load(observer/'complete.private.json');terminal_path=observer/'native.private.bin';terminal=load(terminal_path)
    first=load(args.case_plan.parent/'native-first-start.private.json');launch=load(args.case_plan.parent/'launch/result.private.json')
    need(completed['completed'] and completed['POSTs']==3 and completed['automatic_retries']==0 and
         completed['model_source_GPU_owners_positively_retired'] and completed['native_binding']==first,
         'Complete once-only normal API, frame and resource evidence required')
    need(terminal['completed'] and terminal['pid']==first['pid'] and terminal['run_id']==case['run_id'] and
         terminal['candidate_SELF_sha256']==case['SELF']['sha256'] and terminal['model_receipt_sha256']==first['model_receipt_sha256'] and
         terminal['HTTP_requests']==2 and terminal['VideoOut_starts']==1 and terminal['passive_monitor_and_API_completed'] and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         terminal['full_F32_continuation_and_routes_passed'] and terminal['source_windows']==terminal['source_completed_windows'],
         'Exact native owner and positive completed model/source/device retirement required')
    rows=terminal['requests']
    need(len(rows)==3 and all(r['request_reset_completed'] and r['full_F32_finite'] and type(r['counting_quality_passed']) is bool for r in rows),
         'All three original finite requests must positively complete')
    need(launch['completed'] and launch['operation_calls']==1 and launch['app_id']>0,'One accepted ordinary native launch required')
    args.out.mkdir(parents=True,exist_ok=False)
    remote=PHYSICAL+case['report'][5:]
    reports=[dict(record(terminal_path),remote=remote),dict(record(observer/'native.arm2.result.private.bin'),remote=remote+'.arm2.result')]
    close=dict(completed=True,all_model_source_device_owners_positively_retired=True,device_ledger_live_bytes=0,
        pid=first['pid'],app_id=launch['app_id'],reports=reports)
    state_path=args.current/'active-console.private.json';state=load(state_path)
    need(state['active_successful_native_case']['run_id']==case['run_id'] and state['native_running'], 'Exact active native case required')
    state.update(model_loaded=False,unknown_completion=False,state='current_model_positively_retired_ordinary_close_pending')
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    lan=lan_module();boot=load(case['model_proof']['path'])['current_boot']
    journal=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(first['pid'])+'.stages'
    deadline=time.monotonic()+5
    while True:
        stages=lan.web('/fs'+urllib.parse.quote(journal,safe='/'),8<<20)
        if b'resident_additional_completed_waiting_for_ordinary_close' in stages:break
        need(time.monotonic()<deadline,'Complete native terminal journal is pending; retain owner');time.sleep(.1)
    stage_path=args.out/'completed-native-stages.private.log';stage_path.write_bytes(stages)
    reports.append(dict(record(stage_path),remote=journal))
    plan=build(args.workspace,args.mount_plan,case['new_files'],case['new_files'],[],'close',args.out/'ordinary-close',close=close)
    execute(lan,plan,args.out/'ordinary-close')
    deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
            owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
        if not owners:break
        need(time.monotonic()<deadline,'Ordinary close retirement unknown; never retry it');time.sleep(.25)
    old=current_files(args.current);need(old==case['old_files'],'Selected original files changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id']
    pending=[dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json'))
             for i,row in enumerate(old[:3])]
    restoration=build(args.workspace,args.mount_plan,case['new_files'],old,pending,'publish',args.out/'restore')
    publish(lan,pending,restoration,args.out/'restore')
    state.update(state='current_model_completed_ordinarily_closed_original_restored',native_running=False,model_loaded=False,
        gateway_running=False,native_owners=0,unknown_completion=False,original_restored=True,
        current_boot_Qwen_model_admitted=True,current_boot_readmission_pending=False)
    state.pop('temporary_installed_SELF',None)
    state['active_successful_native_case'].update(phase='model-complete-ordinary-close-original-restored',native_pid=first['pid'])
    state['successful_route_20261102']['native_model_admission_complete']=True
    state['successful_route_20261102']['current_boot_model_proof']=dict(native_terminal=record(terminal_path),
        observer=record(observer/'complete.private.json'),case=record(args.case_plan),SELF=case['SELF'])
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=dict(completed=True,native_model_requests=3,external_API_requests=2,positive_native_frames=2,
        all_model_source_device_owners_positively_retired=True,device_ledger_live_bytes=0,
        ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
        native_owners=0,unknown_completion=False,initializer_requests=0,automatic_retries=0,
        native_terminal=record(terminal_path),observer=record(observer/'complete.private.json'),
        all_counting_quality_passed=all(r['counting_quality_passed'] for r in rows),
        optimization_benefit_qualified=False,production_adopted=False)
    save(args.out/'result.private.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('native_terminal','observer')}))


if __name__=='__main__':main()
