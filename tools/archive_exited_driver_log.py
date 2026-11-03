#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Archive one closed exited-owner log using the successful ownership handoff."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from build_performance_quantizer import record
from run_native_paired_down import completed_operation
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,current_files,lan_module

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--log-kind',choices=('driver','entry'),default='driver')
    p.add_argument('--single-owner-controls',type=Path,help='Reuse the exact completed count-one owner controls')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    case=load(a.case/'plan.private.json');restored=load(a.case/'process-exited-restoration/result.private.json')
    need(restored['completed'] and restored['native_process_exit_observed'] and restored['exact_current_seven_restored_and_native_hashed'],
         'Positive process absence and exact restoration required; no normal-exit assertion is made')
    first_path=a.case/'observed-first.private.json'
    if not first_path.exists():first_path=a.case/'ongoing-first.private.json'
    first=load(first_path);need(first['run_id']==case['run_id'] and
        first['candidate_SELF_sha256']==case['SELF']['sha256'],'Exact exited standalone owner required');lan=lan_module()
    with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:raw=response.read(1<<20)
    need(not [r for r in json.loads(raw)['processes'] if r['name']=='eboot.bin' or r['pid']==first['pid']],
         'The exact exited owner must remain absent')
    (a.out/'processes-before.private.json').write_bytes(raw)
    boot=load(a.current/'active-console.private.json')['current_boot']
    name=('plan-'+case['run_id']+'.json.driver.log' if a.log_kind=='driver' else
          'entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(first['pid'])+'.private.log')
    physical=PHYSICAL+'/qwen-runtime/'+name;alias=ALIAS+'/qwen-runtime/'+name
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=15);ftp.login()
        need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Exact raw transfer mode required')
        ftp.voidcmd('TYPE I');size=ftp.size(physical)
    need(type(size) is int and 0<size<=1<<20,'One exact closed small driver journal required')
    old=(ROOT/'native/qwen_flash_next/closed_log_owner.h').read_text()
    need(old.count('original[17]')==1 and old.count('CASE_CLOSED_LOG_COUNT!=17u')==1,'Exact original closed-owner adapter required')
    owner=old.replace('original[17]','original[1]').replace('CASE_CLOSED_LOG_COUNT!=17u','CASE_CLOSED_LOG_COUNT!=1u').replace('count=17 mode_changes','count=1 mode_changes')
    (a.out/'closed_log_owner.h').write_text(owner,encoding='utf-8',newline='\n')
    test=(ROOT/'tests/closed_log_owner_test.c').read_text()
    test=test.replace('CASE_CLOSED_LOG_COUNT 17u','CASE_CLOSED_LOG_COUNT 1u').replace('[17]','[1]').replace('i>=17','i>=1').replace('i<17','i<1')
    test=test.replace('files[3]','files[0]').replace('scenario<8','scenario<3').replace('calls!=17','calls!=1').replace('changes!=17','changes!=1').replace('cases\\\":8','cases\\\":3')
    source=a.out/'single-closed-owner-test.c';source.write_text(test,encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'single-owner-test.exe'
    jobs=[[str(host/'clang.exe'),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(a.out),str(source),'-o',str(exe)],[str(exe)]]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    if a.single_owner_controls:
        prior=load(a.single_owner_controls);previous=a.single_owner_controls.parent
        prior_intent=load(previous/'intent.private.json')
        need(prior['completed'] and prior_intent['new_single_count_controls']==3 and
             prior_intent['source_owner']==record(ROOT/'native/qwen_flash_next/closed_log_owner.h') and
             prior_intent['source_export']==record(ROOT/'native/qwen_flash_next/closed_log_export.h') and
             (previous/'closed_log_owner.h').read_text()==owner and
             (previous/'single-closed-owner-test.c').read_text()==test and
             b'"cases":3' in (previous/'1.private.log').read_bytes(),
             'Only exact already completed single-owner implementation controls may be reused')
    else:
        for i,job in enumerate(jobs):
            run=subprocess.run(job,capture_output=True,timeout=30,env=env);(a.out/(str(i)+'.private.log')).write_bytes(run.stdout+run.stderr)
            need(run.returncode==0,run.stderr.decode(errors='replace')[-3000:])
    context='struct ClosedLog{const char*path;const char*alias;unsigned long long bytes;};\n#define CASE_CLOSED_LOG_COUNT 1u\n'
    context+='static const struct ClosedLog case_closed_logs[]={{'+json.dumps(physical)+','+json.dumps(alias)+','+str(size)+'ULL}};\n'
    context+='#define case_retire_completed_images case_handoff_closed_log\n'+owner+'\n#undef case_retire_completed_images\n'
    context+='#define CASE_PRIOR_ARCHIVE_SHA256 '+json.dumps(record(a.case/'process-exited-restoration/result.private.json')['sha256'])+'\n'
    exporter=(ROOT/'native/qwen_flash_next/closed_log_export.h').read_text().replace('prior_archive_sha256=','process_exit_restoration_sha256=')
    context+=exporter+'\nstatic int case_retire_completed_images(int*calls){return case_handoff_closed_log(calls)&&case_export_closed_logs(calls);}\n'
    rows=current_files(a.current);need(rows==case['old_files'],'Only the exact restored production is admitted')
    plan=build(a.workspace,a.mount_plan,rows,rows,[],'retire-completed-images',a.out/'native',completed_images_context=context)
    save(a.out/'intent.private.json',dict(case=record(a.case/'plan.private.json'),process_exit_restoration=record(a.case/'process-exited-restoration/result.private.json'),
        log=dict(physical=physical,alias=alias,bytes=size),owner_transition=[1,0],mode='0600',payload_writes=0,
        current_seven_unchanged=True,source_owner=record(ROOT/'native/qwen_flash_next/closed_log_owner.h'),
        source_export=record(ROOT/'native/qwen_flash_next/closed_log_export.h'),new_single_count_controls=3,
        reused_single_count_controls=record(a.single_owner_controls) if a.single_owner_controls else None,
        log_kind=a.log_kind,
        normal_exit_claimed=False,explicit_log_handling_authorized=True,title_launches=0,GPU_calls=0))
    result=completed_operation(lan,plan,a.out/'native')
    need(result['completed'] and result['operation_calls']==2,'One owner handoff and one read-only archive open required')
    journal=Path(result['raw']['path']).read_bytes();data=bytearray()
    for offset,hex_bytes in re.findall(rb'CLOSED_LOG_BYTES ordinal=0 offset=(\d+) hex=([0-9a-f]+)',journal):
        need(int(offset)==len(data),'Every archived driver-log byte must be contiguous');data.extend(bytes.fromhex(hex_bytes.decode()))
    seals=re.findall(rb'CLOSED_LOG_SEALED ordinal=0 bytes=(\d+) sha256=([0-9a-f]{64}) full_identity_and_EOF=1',journal)
    need(len(seals)==1 and len(data)==size==int(seals[0][0]) and hashlib.sha256(data).hexdigest()==seals[0][1].decode(),
         'The independent native whole SHA256, EOF and complete exported bytes must agree')
    archive=a.out/('closed-'+a.log_kind+'.private.log');archive.write_bytes(data)
    save(a.out/'result.private.json',dict(completed=True,archived_log=record(archive),whole_native_and_host_SHA256_equal=True,
        physical_and_alias_identity_equal=True,closed_owner_PID=first['pid'],owner_transition=[1,0],mode_changes=0,
        source_payload_writes=0,current_seven_preserved_and_native_hashed=True,native=record(a.out/'native/result.private.json'),
        source_log_lines=len(data.splitlines()),normal_native_exit_claimed=False,title_launches=0,GPU_calls=0,initializer_requests=0))
    print(json.dumps(dict(completed=True,archived_bytes=size,lines=len(data.splitlines()),current_seven_preserved=True,GPU_calls=0)))


if __name__=='__main__':main()
