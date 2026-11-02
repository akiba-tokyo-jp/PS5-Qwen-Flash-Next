#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ordinarily close a source-audited synchronous pre-main SELF-read refusal."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.parse

from build_performance_quantizer import record
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    case=load(args.case_plan);observation=load(args.case_plan.parent/'host-early-self-refusal.private.json')
    need(observation['case_plan']==record(args.case_plan) and not observation['native_failure_JSON_present'],
         'The exact host-observed pre-main journal refusal is required')
    journal=observation['journal'];need(record(journal['path'])=={k:journal[k] for k in ('path','bytes','sha256')},'Observed journal changed')
    native=load(args.current/'provenance/native-link.receipt.private.json');selected=native['resident_main_SELF']
    template=ROOT/'native/app/resident_early_SELF.c'
    normalized_template=template.read_text(encoding='utf-8').encode()
    need(len(normalized_template)==selected['pure_C_template']['bytes'] and
         hashlib.sha256(normalized_template).hexdigest()==selected['pure_C_template']['sha256'],
         'The actual early SELF template changed beyond working-tree line endings')
    # Execute only the historical pure string-generation prefix, stopping
    # before any build, publication, subprocess or console operation.
    generator=ROOT/'tools/build_main_SELF.py';tree=ast.parse(generator.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');prefix=[]
    for node in function.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='needle' for t in node.targets):break
        prefix.append(node)
    module=ast.Module(body=prefix,type_ignores=[]);ast.fix_missing_locations(module)
    namespace=dict(ROOT=ROOT,__file__=str(generator));exec(compile(module,str(generator)+'#source-only','exec'),namespace)
    source=namespace['source'];raw_source=source.encode();expected=selected['pure_C_source']
    need(len(raw_source)==expected['bytes'] and hashlib.sha256(raw_source).hexdigest()==expected['sha256'],
         'The complete actual main-entry SELF C source must be recovered byte-for-byte')
    window=1048576
    if case.get('package'):
        need(record(case['package']['path'])==case['package'],'The actual accepted package changed')
        package=load(case['package']['path']);effective=package.get('effective_application_policy',{})
        if effective.get('kind') in ('CPU-SELF-window','Q1-shared','Q2-calibration','Q2-IQ2-fixture'):
            profile=load(effective['profile']['path']);need(record(effective['profile']['path'])==effective['profile'],'Compiled startup scope changed')
            provider=profile['CPU_SELF_provider'];window=provider['window_bytes']
            need(window==65536 and provider['parent_source']==expected and provider['OS_minimum_plus_21_unchanged'],
                 'Only the separately compiled smaller-window scope is admitted')
            need(record(provider['source']['path'])==provider['source'] and record(provider['artifact']['path'])==provider['artifact'],
                 'The actual changed CPU provider changed')
            source=source.replace('WINDOW=1048576','WINDOW=65536',1).replace('window_bytes=1048576','window_bytes=65536',1)
            need(source.encode()==Path(provider['source']['path']).read_bytes(),'The complete actual smaller reader differs beyond its two window constants')
            raw_source=source.encode()
    need('pread(fd,buffer,WINDOW,(off_t)offset);++result.read_calls;' in source and
         'early_SELF_Direct_read_returned GPU_calls=0' in source and
         'if(!sample()||!now()||now()-start>' in source and 'return 0;' in source and
         'std::thread' not in source and 'pthread_create' not in source,'Only synchronous returned CPU I/O is admitted')
    lan=lan_module();stages=lan.web('/fs'+urllib.parse.quote(journal['remote'],safe='/'),8<<20)
    need(stages==Path(journal['path']).read_bytes() and
         stages.endswith(b'fatal_operation=main_SELF_Direct_integrity_returned_refusal\n') and
         stages.count(b'early_SELF_Direct_read_before_native_call GPU_calls=0')>0 and
         stages.count(b'early_SELF_Direct_read_before_native_call GPU_calls=0')==stages.count(b'early_SELF_Direct_read_returned GPU_calls=0') and
         b'CXX_initializers_completed\n' in stages and
         b'main_entered GPU_not_started=1 model_loaded=0' not in stages and
         b'configuration_read' not in stages and b'model_mapping_' not in stages and b'inference_before_' not in stages,
         'The exact first returned SELF read, subsequent sample refusal and pre-main halt are required')
    counters=re.findall(rb'main_SELF_CPU_observation free_before=(\d+) free_last=(\d+) minimum_sampled=(\d+) selected_CPU_floor=(\d+) completed_reads=(\d+)',stages)
    need(len(counters)==1,'One completed CPU scope observation is required')
    free_before,free_last,minimum,floor,reads=map(int,counters[0])
    need(free_before>=floor and free_last==minimum<floor and floor==919 and reads>0 and
         reads==stages.count(b'early_SELF_Direct_read_returned GPU_calls=0') and b'early_SELF_Direct_EOF_' not in stages,
         'Only the observed synchronous partial-read sample refusal with no outstanding read is admitted')
    base=PHYSICAL+case['report'][5:];lan.absent(base+'.first.start');lan.absent(base+'.failure');lan.absent(base+'.fatal')
    launch=load(args.case_plan.parent/'launch/result.private.json');need(launch['completed'] and launch['operation_calls']==1,'One accepted launch required')
    with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
        owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
    need(len(owners)==1 and int(owners[0]['pid'])==observation['pid'],'The same exact pre-main owner is required')
    resident=load(args.case_plan.parent/'development.json')['native_resident_launch_integrity']
    receipt_remote=PHYSICAL+resident['receipt_path'][5:]
    receipt=lan.web('/fs'+urllib.parse.quote(receipt_remote,safe='/'),1<<20)
    receipt_path=args.out/'launch-receipt.private.json';receipt_path.write_bytes(receipt)
    bound=json.loads(receipt);need(bound['run_id']==case['run_id'],'The exact successful launch-integrity receipt is required')
    reports=[journal,dict(record(receipt_path),remote=receipt_remote)]
    source_path=args.out/'actual-early-self.private.c';source_path.write_bytes(raw_source)
    save(args.out/'source-audit.private.json',dict(completed=True,actual_source=record(source_path),expected_source=expected,
        synchronous_reads_started=reads,synchronous_reads_returned=reads,GPU_calls=0,model_probe_ranges_started=0,
        application_Direct_bytes_retained_until_ordinary_OS_close=window,
        pre_close_unmap_or_release_claimed=False,ordinary_OS_close_releases_application_owned_backing=True))
    close=dict(CPU_only=True,all_CPU_IO_returned=True,pid=observation['pid'],app_id=launch['app_id'],reports=reports)
    plan=build(args.workspace,args.mount_plan,case['new_files'],case['new_files'],[],'close',args.out/'ordinary-close',close=close)
    execute(lan,plan,args.out/'ordinary-close');deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(r['name']=='eboot.bin' for r in rows):break
        need(time.monotonic()<deadline,'Ordinary exit remains unknown; no retry');time.sleep(.25)
    old=current_files(args.current);need(old==case['old_files'],'Selected current files changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id'];pending=[dict(row,target=row['remote'],remote=prefix+
        ('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')) for i,row in enumerate(old[:3])]
    restoration=build(args.workspace,args.mount_plan,case['new_files'],old,pending,'publish',args.out/'restore')
    publish(lan,pending,restoration,args.out/'restore')
    path=args.current/'active-console.private.json';state=load(path)
    state.update(state='known_early_SELF_CPU_refusal_ordinarily_closed_original_restored',native_running=False,model_loaded=False,
        native_owners=0,unknown_completion=False,original_restored=True)
    state.pop('temporary_installed_SELF',None);state['active_successful_native_case']['phase']='known-early-SELF-refusal-closed-original-restored'
    path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    report=dict(completed=True,known_returned_synchronous_CPU_refusal=True,GPU_initializations=0,model_probe_ranges_started=0,
        ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
        native_owners=0,unknown_completion=False,initializer_requests=0,automatic_retries=0)
    save(args.out/'result.private.json',report);print(json.dumps(report))


if __name__=='__main__':main()
