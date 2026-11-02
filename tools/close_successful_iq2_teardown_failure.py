#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Close only the source-bound IQ2 CPU teardown failure after all GPU work returned."""
import argparse
import json
from pathlib import Path
import time
import urllib.parse

from build_performance_quantizer import record
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL

ENTRY='002b695b4896bfea2d540055656adf5aacd56832b5964cd2ed129b8d04de2150'
RUNTIME='b599c786d3408cd5c0aa4ad6bfc5ed9374d3b04717132ad6551265c41655ad81'
SELF='ea51caa64d9cf38f58db7b723f837495515652cb8fcaba801e28d20268dbdd5c'


def audit_stages(stages):
    lines=stages.splitlines()
    before=b'IQ2_component_graph_before_native_call'
    after=b'IQ2_component_graph_positively_completed'
    need(lines.count(before)==lines.count(after)==72,'Exactly 72 returned component graphs required')
    outstanding=False
    for line in lines:
        if line==before:
            need(not outstanding,'Overlapping graph calls');outstanding=True
        if line==after:
            need(outstanding,'Completion without a graph call');outstanding=False
    need(not outstanding,'An outstanding graph must retain the owner')
    io=b'IQ2_component_Direct_read_before_native_call';returned=b'IQ2_component_Direct_read_returned'
    need(lines.count(io)==lines.count(returned)>0,'Every synchronous component read must return')
    need(lines[-5:]==[b'native_driver_before_positive_device_idle',b'native_driver_device_idle_completed',
        b'native_driver_before_completed_epoch_retirement',b'native_driver_producer_completed_resources_owned',
        b'resident_additional_exception_work_stopped'],'Final positive device/worker/producer completion must precede the CPU exception')
    need(b'model_mapping_all_completed_ranges_unmapped mapped_files=76 unmapped_files=76 GPU_not_started=1 model_loaded=0' in lines,
         'All original virtual probe ranges must have retired')
    need(not any(b'fatal' in line or line.startswith(b'inference_') for line in lines),'No fatal or model inference is admitted')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','entry-receipt','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    case=load(a.case_plan);first=load(a.case_plan.parent/'native-first-start.private.json')
    launch=load(a.case_plan.parent/'launch/result.private.json');entry=load(a.entry_receipt)
    need(record(case['package']['path'])==case['package'] and case['SELF']['sha256']==SELF and
         first['candidate_SELF_sha256']==SELF and first['run_id']==case['run_id'] and
         launch['completed'] and launch['operation_calls']==1,'Only the exact consumed unloaded program is admitted')
    package=load(case['package']['path']);relink=load(package['relink']['path'])
    need(record(package['relink']['path'])==package['relink'],'The accepted link receipt changed')
    for key in ('source','runtime','entry','provider'):
        need(record(entry[key]['path'])==entry[key],'Actual compiled fixture input changed')
    need(entry['source']['sha256']==ENTRY and entry['runtime']['sha256']==RUNTIME,'Only the exact audited complete sources are admitted')
    need(all(relink['link_command'].count(entry[k]['path'])==1 for k in ('entry','provider')),
         'Both audited providers must occur once in the accepted link')
    text=Path(entry['source']['path']).read_text(encoding='utf-8')
    suffix=text[text.index('        auto component=qwen_app::run_calibrated_iq2_fixture'):]
    markers=['auto component=qwen_app::run_calibrated_iq2_fixture','qwen_native_driver_complete();',
        'if(source.chunks!=source.completed_windows)','qwen_app::stop_native_model_sources();',
        '}catch(const std::exception &e){','resident_additional_exception_work_stopped']
    positions=[suffix.index(x) for x in markers];need(positions==sorted(positions),'Exact post-component CPU failure path required')
    # The complete runtime hash binds returned buffer/backend frees, pack close,
    # synchronous reads and bounded loops. No in-process recovery is attempted.
    a.out.mkdir(parents=True,exist_ok=False);lan=lan_module()
    base=PHYSICAL+case['report'][5:];failure_remote=base+'.failure'
    boot=load(case['model_proof']['path'])['current_boot']
    journal=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(first['pid'])+'.stages'
    raw=lan.web('/fs'+urllib.parse.quote(failure_remote,safe='/'),1<<20)
    need(raw==(a.case_plan.parent/'native.failure.private.json').read_bytes(),'The returned failure changed')
    failure=json.loads(raw)
    need(failure['message']=='The post-load device ledger has no healthy admitted producer' and
         failure['native_resources_started'] is True and failure['model_loaded'] is False and
         failure['CPU_worker_completion_unknown'] is False,'Only the exact returned CPU ledger exception is admitted')
    stages=lan.web('/fs'+urllib.parse.quote(journal,safe='/'),8<<20);audit_stages(stages)
    need(stages==(a.case_plan.parent/'native-stages.private.log').read_bytes(),'The parked journal changed')
    time.sleep(.25)
    need(lan.web('/fs'+urllib.parse.quote(journal,safe='/'),8<<20)==stages,'The native owner is still advancing')
    reports=[]
    for name,data,remote in [('failure',raw,failure_remote),('stages',stages,journal)]:
        target=a.out/(name+'.private.log');target.write_bytes(data);reports.append(dict(record(target),remote=remote))
    proof=dict(known_IQ2_CPU_teardown_failure=True,model_loaded=False,GPU_graphs_positively_completed=72,
        all_GGML_backends_retired=True,final_driver_producer_completed=True,all_source_IO_completed=True,
        CPU_worker_completion_unknown=False,source_audit_SHA256=ENTRY,pid=first['pid'],app_id=launch['app_id'],reports=reports)
    save(a.out/'source-audit.private.json',dict(completed=True,entry=entry['source'],runtime=entry['runtime'],
        accepted_SELF=case['SELF'],proof=proof,device_ledger_enabled=False,zero_device_ledger_claimed=False,
        CPU_source_window_and_idle_worker_retained_until_ordinary_OS_close=True,numerics_and_speed_qualified=False))
    plan=build(a.workspace,a.mount_plan,case['new_files'],case['new_files'],[],'close',a.out/'ordinary-close',close=proof)
    if not a.execute:return
    execute(lan,plan,a.out/'ordinary-close');deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(r['name']=='eboot.bin' for r in rows):break
        need(time.monotonic()<deadline,'Ordinary close did not complete; never retry it');time.sleep(.25)
    old=current_files(a.current);need(old==case['old_files'],'Selected current files changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id']
    pending=[dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')) for i,row in enumerate(old[:3])]
    restoration=build(a.workspace,a.mount_plan,case['new_files'],old,pending,'publish',a.out/'restore')
    publish(lan,pending,restoration,a.out/'restore')
    state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['active_successful_native_case']['run_id']==case['run_id'],'Exact active scope required')
    state.update(state='known_completed_IQ2_CPU_teardown_failure_ordinarily_closed_current_restored',
        native_running=False,model_loaded=False,gateway_running=False,native_owners=0,unknown_completion=False,original_restored=True)
    state.pop('temporary_installed_SELF',None)
    state['active_successful_native_case']['phase']='IQ2-CPU-teardown-failure-closed-current-restored'
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=dict(completed=True,ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
        GPU_graphs_positively_completed=72,source_audit=record(a.out/'source-audit.private.json'),
        native_owners=0,unknown_completion=False,initializer_requests=0,automatic_retries=0,numerics_and_speed_qualified=False)
    save(a.out/'result.private.json',result);print(json.dumps(result))


if __name__=='__main__':main()
