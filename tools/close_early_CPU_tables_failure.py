#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ordinarily close only a positively returned source-bound CPU prelude failure."""
import argparse
import json
from pathlib import Path
import time
import urllib.parse
from build_performance_quantizer import record
from early_CPU_tables_completion import review
from price_cpu_startup_original_reader import require_CPU_profile
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import PHYSICAL,build,current_files,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','direct-staging-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);case=load(a.case_plan)
    observation=load(a.case_plan.parent/'host-early-CPU-tables-refusal.private.json')
    need(observation['case_plan']==record(a.case_plan) and record(case['package']['path'])==case['package'],'Exact accepted CPU case required')
    package=load(case['package']['path'])
    if package.get('early_model_CPU_tables'):
        from early_model_table_scope import require as require_early_model
        early=require_early_model(package)
    else:
        package,profile=require_CPU_profile(case['package']['path']);early=package['early_CPU_tables']
    for key in ('source','header','manifest','control_native'):
        need(record(early[key]['path'])==early[key],'A source-bound CPU prelude input changed')
    source=Path(early['source']['path']).read_text()
    need(all(word not in source for word in ('pthread_create','std::thread','vkCreate','pread(','open(')) and
        source.count('sceKernelAllocateDirectMemory(')==source.count('sceKernelMapDirectMemory(')==1 and
        (early.get('prelude_GPU_and_source_operations')==0 or
         early.get('model_GPU_operations')==early.get('source_payload_IO')==0) and early['strict_failure_park_before_original_application_CXX'],
        'Only the fixed synchronous source-free CPU prelude is admitted')
    journal=observation['journal'];need(record(journal['path'])=={k:journal[k] for k in ('path','bytes','sha256')},'Bound CPU journal changed')
    lan=lan_module();raw=lan.web('/fs'+urllib.parse.quote(journal['remote'],safe='/'),8<<20)
    need(raw==Path(journal['path']).read_bytes(),'The same exact parked CPU boundary is required')
    reviewed=review(raw,early['control_native']['path']);save(a.out/'source-audit.private.json',dict(reviewed,source=early['source'],package=case['package']))
    launch=load(a.case_plan.parent/'launch/result.private.json');need(launch['completed'] and launch['operation_calls']==1,'One already accepted title required')
    with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
        owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
    need(len(owners)==1 and int(owners[0]['pid'])==observation['pid'],'The same exact CPU owner must remain')
    state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['current_boot']==observation['boot'] and state['active_successful_native_case']['run_id']==case['run_id'] and
        state['native_running'] and not state['original_restored'],'The same accepted boot/run is required')
    state.update(unknown_completion=False,native_owners=1,observed_native_pid=observation['pid']);state_path.write_text(json.dumps(state,indent=2)+'\n')
    resident=load(a.case_plan.parent/'development.json')['native_resident_launch_integrity']
    receipt_remote=PHYSICAL+resident['receipt_path'][5:]
    receipt=lan.web('/fs'+urllib.parse.quote(receipt_remote,safe='/'),1<<20)
    receipt_path=a.out/'launch-receipt.private.json';receipt_path.write_bytes(receipt)
    need(json.loads(receipt)['run_id']==case['run_id'],'The exact native launch-integrity receipt is required')
    proof=dict(CPU_only=True,all_CPU_IO_returned=True,pid=observation['pid'],app_id=launch['app_id'],
        reports=[journal,dict(record(receipt_path),remote=receipt_remote)])
    close=build(a.workspace,a.mount_plan,case['new_files'],case['new_files'],[],'close',a.out/'ordinary-close',close=proof)
    execute(lan,close,a.out/'ordinary-close');until=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(r['name']=='eboot.bin' for r in rows):break
        need(time.monotonic()<until,'Ordinary exit remains unknown; never repeat close');time.sleep(.25)
    old=current_files(a.current);need(old==case['old_files'],'Selected production changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id'];pending=[dict(row,target=row['remote'],remote=prefix+
        ('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')) for i,row in enumerate(old[:3])]
    restore=build(a.workspace,a.mount_plan,case['new_files'],old,pending,'publish',a.out/'restore')
    publish(lan,pending,restore,a.out/'restore',direct_staging=dict(workspace=a.workspace,mount_plan=a.mount_plan,qualified=a.direct_staging_proof))
    state=load(state_path);state.update(state='known_early_CPU_tables_returned_ordinarily_closed_original_restored',native_running=False,
        model_loaded=False,native_owners=0,unknown_completion=False,original_restored=True)
    state.pop('temporary_installed_SELF',None);state['active_successful_native_case']['phase']='early-CPU-tables-failure-ordinary-close-original-restored'
    state_path.write_text(json.dumps(state,indent=2)+'\n')
    save(a.out/'result.private.json',dict(completed=True,known_returned_CPU_tables_failure=True,source_audit=record(a.out/'source-audit.private.json'),
        ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
        native_owners=0,unknown_completion=False,model_GPU_calls=0,initializer_requests=0,automatic_retries=0))
    print(dict(completed=True,ordinary_close_calls=1,current_restored=True,model_GPU_calls=0))


if __name__=='__main__':main()
