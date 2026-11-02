#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Restore the selected application after a positively returned launch refusal."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from staged_self_upload import upload
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','case-plan','mount-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();case=load(args.case_plan);previous=args.case_plan.parent
    launch=load(previous/'launch/result.private.json')
    raw=(previous/'launch/execution/console.private.log').read_bytes()
    need(launch['helper_exited'] and not launch['completed'] and launch['operation_calls']==1 and
         re.search(rb'RETURN LaunchApp rc=-[0-9]+ canaries=1\n',raw),
         'A positively returned OS launch refusal is required; no unknown execution')
    old=current_files(args.current);need(old==case['old_files'],'Selected original application changed')
    pending=[];staging='/data/ai/moss-qwen-case-'+case['run_id']
    for i,row in enumerate(old[:3]):
        remote=staging+'-restore-SELF.bin' if i==0 else staging+'-restore-'+str(i)+'.json'
        pending.append(dict(row,remote=remote,target=row['remote']))
    plan=build(args.workspace,args.mount_plan,case['new_files'],old,pending,'publish',args.out)
    lan=lan_module()
    with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
    need(not any(r['name']=='eboot.bin' for r in rows),'No native title owner is required before restoration')
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw transfer mode required')
        for row in pending[1:]:
            lan.absent(row['remote']);need(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},'Original metadata changed')
            with Path(row['path']).open('rb') as stream:reply=ftp.storbinary('STOR '+row['remote'],stream,65536)
            need(reply.startswith(('226 ','250 ')),'Metadata transfer incomplete')
    def verify(capture,remote):
        need(remote==pending[0]['remote'],'Exact selected SELF restoration required')
        result=execute(lan,plan,args.out);need(result['operation_calls']==3,'All three startup files must restore')
        return dict(whole_native_SHA256_identity_EOF_verified=True,all_reads_returned=True,
                    sha256=capture['sha256'],bytes=capture['bytes'])
    upload({k:old[0][k] for k in ('path','bytes','sha256')},pending[0]['remote'],args.out/'SELF-transfer',lan,verify)
    path=args.current/'active-console.private.json';state=load(path)
    state.update(state='runtime_and_mount_ready_OS_launch_refused_original_restored',native_running=False,
                 model_loaded=False,gateway_running=False,native_owners=0,unknown_completion=False,original_restored=True)
    state.pop('temporary_installed_SELF',None)
    state['active_successful_native_case'].update(phase='OS-launch-refused-original-restored',restoration=record(args.out/'result.private.json'))
    path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(original_restored=True,current_seven_native_hashes_pass=True,native_owners=0,
                          initializer_requests=0,title_launches=0,GPU_calls=0)))


if __name__=='__main__':main()
