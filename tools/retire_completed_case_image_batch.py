#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove exact displayed BMPs from several independently positively closed cases."""
import argparse
import json
from pathlib import Path
import re
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,digest_expression,execute,lan_module


def prepare(case_record,current,state):
    completed=load(case_record)
    for key in ('case_plan','close','native_terminal'):need(record(completed[key]['path'])==completed[key],'Closed-case evidence changed')
    case=load(completed['case_plan']['path']);closed=load(completed['close']['path']);terminal=load(completed['native_terminal']['path'])
    need(completed['all_intended_events_exercised'] and closed['completed'] and closed['ordinary_exit_observed'] and
         closed['current_seven_restored_and_native_hashed'] and not closed['unknown_completion'] and terminal['completed'] and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and len(terminal['requests'])==3,
         'Only positively completed and ordinarily restored three-request model cases are admitted')
    need(re.fullmatch('[0-9a-f]{32}',case['run_id']) and case['report']=='/app0/qwen-runtime/plan-'+case['run_id']+'.json' and
         state['active_successful_native_case']['run_id']!=case['run_id'],'The active/latest case is protected')
    latest=state['successful_route_20261102']['current_boot_model_proof']['case']
    need(Path(latest['path']).resolve()!=Path(completed['case_plan']['path']).resolve(),'The current real-model proof is protected')
    root=Path(completed['case_plan']['path']).parent;observer=root/'passive-observer';observed=load(observer/'complete.private.json')
    frames=observed['actual_native_frames']
    need(observed['completed'] and observed['model_source_GPU_owners_positively_retired'] and len(frames)==2 and
         all(frame['positive_VideoOut_completion'] and frame['run_id']==case['run_id'] and frame['pid']==terminal['pid'] for frame in frames),
         'Two positively completed actually displayed native frames required')
    targets=[];campaign=(current.parent/'performance-20261102').resolve()
    for ordinal,frame in zip((1,2),frames):
        path=(observer/('native.arm'+str(ordinal)+'.display.bmp.private.bin')).resolve()
        need(path.is_relative_to(campaign) and not path.is_symlink(),'Only exact owned campaign image copies are admitted')
        value=record(path);need(value['bytes']==frame['BMP_bytes'] and 54<value['bytes']<=16<<20,'Full independent bounded PC BMP copy required')
        remote=PHYSICAL+case['report'][5:]+'.arm'+str(ordinal)+'.display.bmp'
        targets.append(dict(value,remote=remote,alias=ALIAS+remote[len(PHYSICAL):]))
    reports=[dict(completed['native_terminal'],remote=PHYSICAL+case['report'][5:]),
        dict(record(observer/'native.arm2.result.private.bin'),remote=PHYSICAL+case['report'][5:]+'.arm2.result')]
    return dict(case_record=record(case_record),case_plan=completed['case_plan'],closed=completed['close'],targets=targets,reports=reports)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--case-record',type=Path,action='append',required=True)
    p.add_argument('--remove-host-copies',action='store_true');p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true')
    a=p.parse_args();need(1<=len(a.case_record)<=16 and not(a.execute and a.collect),'One bounded list and one native submission/collection phase required')
    state=load(a.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Positive idle current deployment required')
    cases=[prepare(path,a.current,state) for path in a.case_record];targets=[dict(target,case_index=index) for index,case in enumerate(cases) for target in case['targets']]
    need(len({row['remote'] for row in targets})==len(targets),'Each exact image may appear only once')
    package=load(a.current/'provenance/current-package.private.json');native=load(a.current/'provenance/native-link.receipt.private.json')
    selected=current_files(a.current)+load(a.current/'provenance/retained-relink-inputs.private.json')+native['formatter_stubs']+[package['formatter']]
    protected={Path(row['path']).resolve():record(row['path']) for row in selected}
    need(all(all(protected[Path(row['path']).resolve()][key]==row[key] for key in ('bytes','sha256')) for row in selected),
         'All selected production/compiler/formatter inputs must remain exact')
    need(all(Path(row['path']).resolve() not in protected for row in targets),'Selected files are protected')
    lan=lan_module()
    if a.collect:
        intent=load(a.out/'intent.private.json');need(intent['targets']==targets,'Consumed deletion targets changed')
        plan=load(a.out/'native/plan.private.json');need((a.out/'native/execution/execution.once.private.json').exists(),'Collect only the already consumed operation')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,a.out/'native',raw,path)
    else:
        a.out.mkdir(parents=True,exist_ok=False);save(a.out/'intent.private.json',dict(cases=cases,targets=targets,
            protected=list(protected.values()),remove_host_copies=a.remove_host_copies,recursive_operations=0))
        context='struct CompletedImage{const char*path;const char*alias;unsigned long long bytes;const char*sha256;unsigned case_index;};\n'
        context+='static const struct CompletedImage case_images[]={'+','.join('{'+','.join([json.dumps(row['remote']),json.dumps(row['alias']),str(row['bytes'])+'ULL',json.dumps(row['sha256']),str(row['case_index'])])+'}' for row in targets)+'};\n'
        context+='static unsigned case_image_index;\n#define CASE_COMPLETED_FILE_KIND "image"\n#define CASE_COMPLETED_FILE_LABEL "IMAGE"\n'
        context+='#define CASE_ACTIVATION_PATH case_images[case_image_index].path\n#define CASE_ACTIVATION_ALIAS case_images[case_image_index].alias\n'
        context+='#define CASE_ACTIVATION_BYTES case_images[case_image_index].bytes\n#define CASE_ACTIVATION_SHA256 case_images[case_image_index].sha256\n'
        context+='static int case_completed_activation_reports_valid(void){switch(case_images[case_image_index].case_index){'
        for index,case in enumerate(cases):context+='case '+str(index)+':return '+'&&'.join(digest_expression(row) for row in case['reports'])+';'
        context+='default:return 0;}}\n#include "activation_capture_retire.h"\n'
        context+='static int case_retire_completed_images(int*calls){for(case_image_index=0;case_image_index<'+str(len(targets))+';++case_image_index){if(!report("IMAGE_BATCH_TARGET ordinal=%u",case_image_index)||!case_retire_activation(calls))return 0;}return 1;}\n'
        current=current_files(a.current);plan=build(a.workspace,a.mount_plan,current,current,[],'retire-completed-images',a.out/'native',completed_images_context=context)
        if not a.execute:return
        # Whole-file checks for a batch can exceed the shared helper client's
        # default1MiB journal read bound. Increase only this exact new journal;
        # native submission count, observation deadline and all other reads stay
        # unchanged. A failed collection still must never resubmit the helper.
        original_web=lan.web;expected_log='/fs'+urllib.parse.quote(plan['log'],safe='/')
        def bounded_web(path,limit=1<<20,timeout=15):
            return original_web(path,64<<20 if path==expected_log else limit,timeout)
        lan.web=bounded_web
        try:result=execute(lan,plan,a.out/'native',observation_seconds=60)
        finally:lan.web=original_web
    need(result['completed'] and result['operation_calls']==len(targets),'Every exact native unlink and directory-owner restoration must return positively')
    if a.remove_host_copies:
        for row in targets:
            path=Path(row['path']);need(record(path)=={key:row[key] for key in ('path','bytes','sha256')},'An independently matched PC image changed')
            path.unlink()
    need(all(record(path)==value for path,value in protected.items()),'A selected input changed during cleanup')
    save(a.out/'result.private.json',dict(completed=True,retired_console_images=len(targets),retired_console_bytes=sum(row['bytes'] for row in targets),
        retired_PC_images=len(targets) if a.remove_host_copies else 0,retired_PC_bytes=sum(row['bytes'] for row in targets) if a.remove_host_copies else 0,
        selected_files_protected=len(protected),all_selected_whole_SHA256_values_unchanged=True,
        both_console_namespaces_absent=True,original_runtime_directory_owner_restored=True,latest_model_proof_protected=True,
        native=record(a.out/'native/result.private.json'),GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,retired_console_images=len(targets),retired_PC_images=len(targets) if a.remove_host_copies else 0,
        selected_files_protected=len(protected),GPU_calls=0)))


if __name__=='__main__':main()
