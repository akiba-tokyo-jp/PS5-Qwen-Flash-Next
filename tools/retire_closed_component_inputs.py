#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire the two exact archived, positively closed Q2/Q3 component input files."""
import argparse
import json
from pathlib import Path
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,digest_expression,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','campaign','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true');a=p.parse_args()
    need(not(a.execute and a.collect),'Submit once or collect the same operation')
    state=load(a.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Positive idle restoration required')
    q2root=a.campaign/'Q2-explicit-F32-assigned-port-native-64820';q2=load(q2root/'result.private.json')
    q2close=load(q2['closure']['path']);component=load(q2['component']['path']);q2case=load(q2['case']['path'])
    terminal_path=q2root/'case/headless-observer/native.private.bin';terminal=load(terminal_path)
    need(q2['completed'] and q2close['ordinary_exit_observed'] and q2close['current_seven_restored_and_native_hashed'] and
         not q2close['unknown_completion'] and component['all_backends_positively_retired'] and component['all_outputs_reference_valid'] and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0,
         'Completed and ordinarily closed Q2 input consumers required')
    package=load(q2case['package']['path']);profile=load(package['effective_application_policy']['profile']['path']);up=profile['component_pack']
    q3root=a.campaign/'Q3-positive-boundary-close-64872';q3=load(q3root/'result.private.json');audit=load(q3['source_audit']['path'])
    need(record(q3['source_audit']['path'])==q3['source_audit'] and q3['completed'] and q3['ordinary_exit_observed'] and
         q3['current_seven_restored_and_native_hashed'] and not q3['unknown_completion'] and
         audit['final_GPU_and_worker_completion_positive'] and audit['proof']['positive_reference_dispatches']==24 and
         audit['proof']['all_source_IO_completed'] and not audit['proof']['CPU_worker_completion_unknown'],
         'Source-bound positive Q3 completion and ordinary exit required')
    down=load(a.campaign/'Q3-whole-driver-native-64871/component-pack-reuse.private.json')['pack']
    need(up['local']['sha256']=='604446bc6ff4c3bfd2fe1e53ff8da28a30c1aa6c7cb4b365df5cce2be143bd4b' and
         down['sha256']=='e4c908d6947610b303e8419ab4fc6de52c5cc45b1a9bc24cbc566adc0968ea79',
         'Only the two original finite component packs are admitted')
    targets=[dict(up['local'],remote=PHYSICAL+up['application_path'][5:]),
             dict(down,remote=PHYSICAL+'/qwen-runtime/paired-Down-e4c908d6947610b303e8419a.bin')]
    for row in targets:
        need(record(row['path'])=={key:row[key] for key in ('path','bytes','sha256')},'Exact complete PC component input required')
        row['alias']=ALIAS+row['remote'][len(PHYSICAL):]
    reports=[dict(record(terminal_path),remote=PHYSICAL+q2case['report'][5:])]+audit['proof']['reports']
    current=current_files(a.current);selected=current+load(a.current/'provenance/retained-relink-inputs.private.json')
    protected={Path(r['path']).resolve():record(r['path']) for r in selected}
    need(all(all(protected[Path(r['path']).resolve()][k]==r[k] for k in ('bytes','sha256')) for r in selected),'Selected inputs changed')
    lan=lan_module()
    if a.collect:
        intent=load(a.out/'intent.private.json');need(intent['targets']==targets,'Consumed deletion scope changed')
        plan=load(a.out/'native/plan.private.json');need((a.out/'native/execution/execution.once.private.json').exists(),'Collect only the existing operation')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,a.out/'native',raw,path)
    else:
        a.out.mkdir(parents=True,exist_ok=False);save(a.out/'intent.private.json',dict(targets=targets,reports=reports,PC_inputs_preserved=True,recursive_operations=0))
        context='struct ClosedInput{const char*path;const char*alias;unsigned long long bytes;const char*sha256;};\n'
        context+='static const struct ClosedInput inputs[]={'+','.join('{'+','.join([json.dumps(r['remote']),json.dumps(r['alias']),str(r['bytes'])+'ULL',json.dumps(r['sha256'])])+'}' for r in targets)+'};\n'
        context+='static unsigned input_index;\n#define CASE_COMPLETED_FILE_KIND "component_input"\n#define CASE_COMPLETED_FILE_LABEL "COMPONENT_INPUT"\n'
        for key,field in (('PATH','path'),('ALIAS','alias'),('BYTES','bytes'),('SHA256','sha256')):context+='#define CASE_ACTIVATION_'+key+' inputs[input_index].'+field+'\n'
        context+='static int case_completed_activation_reports_valid(void){return '+'&&'.join(digest_expression(r) for r in reports)+';}\n'
        context+='#include "activation_capture_retire.h"\nstatic int case_retire_completed_images(int*calls){for(input_index=0;input_index<2;++input_index)if(!case_retire_activation(calls))return 0;return 1;}\n'
        plan=build(a.workspace,a.mount_plan,current,current,[],'retire-completed-images',a.out/'native',completed_images_context=context)
        if not a.execute:return
        result=execute(lan,plan,a.out/'native',observation_seconds=60)
    need(result['completed'] and result['operation_calls']==2 and all(record(k)==v for k,v in protected.items()),'Both exact retirements and unchanged selected inputs required')
    save(a.out/'result.private.json',dict(completed=True,retired_console_files=2,retired_bytes=sum(r['bytes'] for r in targets),
        PC_inputs_preserved=True,whole_native_and_PC_SHA256_verified=True,both_console_namespaces_absent=True,
        runtime_directory_owner_restored=True,selected_inputs_unchanged=True,native=record(a.out/'native/result.private.json'),
        GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0,RAM_gain_claimed=False))
    print(dict(completed=True,retired_console_files=2,retired_bytes=sum(r['bytes'] for r in targets),GPU_calls=0))


if __name__=='__main__':main()
