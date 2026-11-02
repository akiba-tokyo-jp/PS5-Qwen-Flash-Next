#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire two exact displayed BMP copies from one positively closed model case."""
import argparse
import json
from pathlib import Path
import re
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,execute,lan_module,digest_expression


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-record','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--collect',action='store_true');p.add_argument('--execute',action='store_true');a=p.parse_args()
    need(not(a.collect and a.execute),'One retirement phase required')
    state=load(a.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Positive idle current deployment required')
    completed=load(a.case_record)
    for key in ('case_plan','close','native_terminal'):need(record(completed[key]['path'])==completed[key],'Closed-case evidence changed')
    case=load(completed['case_plan']['path']);closed=load(completed['close']['path']);terminal=load(completed['native_terminal']['path'])
    need(completed['all_intended_events_exercised'] and closed['completed'] and closed['ordinary_exit_observed'] and
         closed['current_seven_restored_and_native_hashed'] and not closed['unknown_completion'] and
         terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         len(terminal['requests'])==3,'Only a positively completed three-request model case is admitted')
    need(re.fullmatch('[0-9a-f]{32}',case['run_id']) and case['report']=='/app0/qwen-runtime/plan-'+case['run_id']+'.json' and
         state['active_successful_native_case']['run_id']!=case['run_id'],'The latest model proof and active scope are protected')
    latest=state.get('successful_route_20261102',{}).get('current_boot_model_proof',{}).get('case')
    if latest:need(Path(latest['path']).resolve()!=Path(completed['case_plan']['path']).resolve(),'The latest completed real-model proof is protected')
    root=Path(completed['case_plan']['path']).parent;observer=root/'passive-observer';observed=load(observer/'complete.private.json')
    frames=observed['actual_native_frames'];need(observed['completed'] and observed['model_source_GPU_owners_positively_retired'] and
        len(frames)==2 and all(f['positive_VideoOut_completion'] and f['run_id']==case['run_id'] and f['pid']==terminal['pid'] for f in frames),
        'Two exact actual displayed frame bindings required')
    targets=[]
    for ordinal,frame in zip((1,2),frames):
        local=observer/('native.arm'+str(ordinal)+'.display.bmp.private.bin');value=record(local)
        need(value['bytes']==frame['BMP_bytes'] and 54<value['bytes']<=16<<20,'One bounded independently copied whole BMP required')
        remote=PHYSICAL+case['report'][5:]+'.arm'+str(ordinal)+'.display.bmp'
        targets.append(dict(value,remote=remote,alias=ALIAS+remote[len(PHYSICAL):]))
    lan=lan_module()
    if a.collect:
        manifest=load(a.out/'plan.private.json');need(manifest['targets']==targets,'The consumed targets changed')
        plan=load(a.out/'native/plan.private.json');need((a.out/'native/execution/execution.once.private.json').exists(),'One consumed operation required')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,a.out/'native',raw,path)
    else:
        a.out.mkdir(parents=True,exist_ok=False)
        proof=dict(completed['native_terminal'],remote=PHYSICAL+case['report'][5:])
        arm=dict(record(observer/'native.arm2.result.private.bin'),remote=proof['remote']+'.arm2.result')
        context='struct CompletedImage{const char*path;const char*alias;unsigned long long bytes;const char*sha256;};\n'
        context+='static const struct CompletedImage case_images[]={'+','.join('{'+','.join([json.dumps(t['remote']),json.dumps(t['alias']),str(t['bytes'])+'ULL',json.dumps(t['sha256'])])+'}'for t in targets)+'};\n'
        context+='static unsigned case_image_index;\n#define CASE_COMPLETED_FILE_KIND "image"\n#define CASE_COMPLETED_FILE_LABEL "IMAGE"\n'
        context+='#define CASE_ACTIVATION_PATH case_images[case_image_index].path\n#define CASE_ACTIVATION_ALIAS case_images[case_image_index].alias\n'
        context+='#define CASE_ACTIVATION_BYTES case_images[case_image_index].bytes\n#define CASE_ACTIVATION_SHA256 case_images[case_image_index].sha256\n'
        context+='static int case_completed_activation_reports_valid(void){return '+digest_expression(proof)+'&&'+digest_expression(arm)+';}\n'
        context+='#include "activation_capture_retire.h"\nstatic int case_retire_completed_images(int*calls){for(case_image_index=0;case_image_index<2;++case_image_index)if(!case_retire_activation(calls))return 0;return 1;}\n'
        current=current_files(a.current)
        plan=build(a.workspace,a.mount_plan,current,current,[],'retire-completed-images',a.out/'native',completed_images_context=context)
        save(a.out/'plan.private.json',dict(case_record=record(a.case_record),targets=targets,closed=completed['close'],
            latest_model_proof_protected=True,selected_current_files=current,native_plan=record(a.out/'native/plan.private.json')))
        if not a.execute:return
        result=execute(lan,plan,a.out/'native',observation_seconds=60)
    need(result['completed'] and result['operation_calls']==2,'Both exact owned image unlinks must return positively')
    save(a.out/'result.private.json',dict(completed=True,retired_images=2,retired_bytes=sum(x['bytes'] for x in targets),
        both_namespaces_absent=True,current_seven_unchanged_and_native_hashed=True,original_runtime_directory_owner_restored=True,
        model_sources_untouched=True,latest_model_proof_protected=True,PC_originals_preserved=True,
        native=record(a.out/'native/result.private.json'),GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,retired_images=2,retired_bytes=sum(x['bytes'] for x in targets),current_seven_unchanged=True)))


if __name__=='__main__':main()
