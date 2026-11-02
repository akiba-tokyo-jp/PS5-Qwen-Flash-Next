#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ordinarily close an explicit pre-GPU exception, then restore selected files."""
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
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    case=load(args.case_plan);start_path=args.case_plan.parent/'native-first-start.private.json'
    launch=load(args.case_plan.parent/'launch/result.private.json')
    need(launch['completed'] and launch['operation_calls']==1,'One accepted native launch required')
    lan=lan_module();base=PHYSICAL+case['report'][5:];early=not start_path.exists()
    if not early:
        start=load(start_path);pid=start['pid']
        need(start['run_id']==case['run_id'] and start['candidate_SELF_sha256']==case['SELF']['sha256'],
             'Exact positively observed native owner required')
    else:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
            owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
        need(len(owners)==1,'Exactly one accepted native owner required for early CPU refusal')
        pid=int(owners[0]['pid'])
        try:lan.absent(base+'.first.start')
        except Exception:raise ValueError('Early refusal already reached model-start scope; retain owner')
    prior=(args.case_plan.parent/'native.failure.private.json').read_bytes()
    failure_raw=lan.web('/fs'+urllib.parse.quote(base+'.failure',safe='/'),1<<20)
    need(prior==failure_raw,'The completed native failure changed')
    failure=json.loads(failure_raw)
    need(failure['native_resources_started'] is False and failure['model_loaded'] is False and
         failure['CPU_worker_completion_unknown'] is False and failure['message'],'Known pre-GPU synchronous exception required')
    import re
    controller=Path(load(args.mount_plan)['controller']['path']).read_text()
    boot=re.search(r'boot.tv_sec!=(\d+)LL\|\|boot.tv_usec!=(\d+)LL',controller)
    remote=PHYSICAL+'/qwen-runtime/entry-b'+boot[1]+'-'+boot[2]+'-'+str(pid)+'.stages'
    stages=lan.web('/fs'+urllib.parse.quote(remote,safe='/'),8<<20)
    if early:
        need(failure['message']=='Monitor clock calibration is stale or inconsistent' and
             b'CXX_initializers_completed' in stages and b'early_SELF_whole_Direct_hash_completed_at_main_entry_after_CXX' in stages and
             b'configuration_read GPU_not_started=1 model_loaded=0' in stages and
             b'resident_additional_exception_work_stopped' in stages and b'model_mapping_' not in stages and
             b'inference_before_' not in stages and b'native_GPU_initialize' not in stages,
             'Only the exact returned pre-model clock refusal with zero started probe ranges is admitted')
    else:
        need(b'model_mapping_all_completed_ranges_unmapped mapped_files=76 unmapped_files=76 GPU_not_started=1 model_loaded=0' in stages and
             b'resident_additional_exception_work_stopped' in stages,'Positive complete probe release and returned exception required')
    reports=[]
    for name,raw,path in (('failure',failure_raw,base+'.failure'),('stages',stages,remote)):
        target=args.out/(name+'.private.log');target.write_bytes(raw);reports.append(dict(record(target),remote=path))
    close=dict(known_returned_pre_GPU_exception=True,native_resources_started=False,model_loaded=False,
               CPU_worker_completion_unknown=False,all_probe_ranges_unmapped=True,pid=pid,app_id=launch['app_id'],reports=reports)
    close['probe_ranges_started']=0 if early else 76
    plan=build(args.workspace,args.mount_plan,case['new_files'],case['new_files'],[],'close',args.out/'ordinary-close',close=close)
    execute(lan,plan,args.out/'ordinary-close')
    deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(r['name']=='eboot.bin' for r in rows):break
        need(time.monotonic()<deadline,'Ordinary close incomplete; no retry');time.sleep(.25)
    old=current_files(args.current);need(old==case['old_files'],'Selected originals changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id'];pending=[]
    for i,row in enumerate(old[:3]):
        pending.append(dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')))
    restoration=build(args.workspace,args.mount_plan,case['new_files'],old,pending,'publish',args.out/'restore')
    publish(lan,pending,restoration,args.out/'restore')
    path=args.current/'active-console.private.json';state=load(path)
    state.update(state='known_pre_GPU_model_exception_ordinarily_closed_current_restored',native_running=False,
                 model_loaded=False,gateway_running=False,native_owners=0,unknown_completion=False,original_restored=True,
                 current_boot_Qwen_model_admitted=False,current_boot_readmission_pending=True)
    state.pop('temporary_installed_SELF',None)
    state['active_successful_native_case'].update(phase='known-pre-GPU-exception-closed-original-restored',failure_message=failure['message'])
    path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=dict(completed=True,known_pre_GPU_exception=True,exception=failure['message'],GPU_initializations=0,
                model_probe_ranges_started=0 if early else 76,
                ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
                native_owners=0,initializer_requests=0,title_launches=0,automatic_retries=0)
    save(args.out/'result.private.json',result);print(json.dumps(result))


if __name__=='__main__':main()
