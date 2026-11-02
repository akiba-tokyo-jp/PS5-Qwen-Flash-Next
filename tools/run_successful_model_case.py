#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind/start one normal model case through the completed successful startup route."""
import argparse
import copy
import json
from pathlib import Path
import secrets
import urllib.parse

from build_performance_quantizer import record
from model_directory_readmission import rebind_directory
from staged_self_upload import upload
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL


def metadata(lan,rows):
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw transfer mode required')
        for row in rows:
            need(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},'Pending metadata changed')
            lan.absent(row['remote'])
            with Path(row['path']).open('rb') as stream:reply=ftp.storbinary('STOR '+row['remote'],stream,65536)
            need(reply.startswith(('226 ','250 ')),'Metadata transfer incomplete')


def publish(lan,rows,plan,out):
    metadata(lan,rows[1:])
    def verify(capture,remote):
        need(remote==rows[0]['remote'],'Exact pending SELF required')
        result=execute(lan,plan,out);need(result['operation_calls']==3,'All three startup publications required')
        return dict(whole_native_SHA256_identity_EOF_verified=True,all_reads_returned=True,
                    sha256=capture['sha256'],bytes=capture['bytes'])
    upload({k:rows[0][k] for k in ('path','bytes','sha256')},rows[0]['remote'],out/'SELF-transfer',lan,verify)


def start(args):
    args.out.mkdir(parents=True,exist_ok=False)
    old=current_files(args.current);proof=load(args.model_proof);state_path=args.current/'active-console.private.json';state=load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and
         not state['unknown_completion'] and not state['current_boot_shader_CPU_proof_pending'],'Completed idle successful route required')
    image={k:old[0][k] for k in ('path','bytes','sha256')}
    if args.package:
        package=load(args.package);need(package['completed'] and package['normalized_SELF_roundtrip_equal'],'Qualified host SELF package required')
        image=package['SELF']
    need(record(image['path'])==image,'Selected SELF changed')
    run=secrets.token_hex(16);nonce=secrets.token_hex(16);report='/app0/qwen-runtime/plan-'+run+'.json'
    policy=load(args.current/'qwen-runtime/development.json');app=load(args.current/'qwen-runtime/app.json')
    gate=rebind_directory(policy['native_first_generation_validation'],proof,proof['current_boot'])
    gate.update(run_id=run,candidate_SELF_bytes=image['bytes'],candidate_SELF_sha256=image['sha256'])
    policy['native_first_generation_validation']=gate
    shader=state['successful_route_20261102']['current_boot_shader_CPU']
    need(record(shader['path'])['sha256']==shader['report_sha256'] and record(shader['path'])['bytes']==shader['report_bytes'],'Current-boot original shader proof changed')
    prior=policy['native_shader_storage']['prior_native_CPU']
    prior.update({k:shader[k] for k in ('report_path','report_bytes','report_sha256','pid','run_id')})
    prior['all_original_assets_completed_on_this_boot']=True
    resident=policy['native_resident_launch_integrity'];resident.update(run_id=run,nonce=nonce,receipt_path='/app0/qwen-runtime/resident-launch-'+run+'.json')
    app.update(admission_report=report,clock_calibration=load(args.clock))
    app_path=args.out/'app.json';policy_path=args.out/'development.json'
    save(app_path,app);save(policy_path,policy)
    updates=[dict(image,remote=old[0]['remote']),dict(record(app_path),remote=old[1]['remote']),dict(record(policy_path),remote=old[2]['remote'])]
    selected={r['remote']:r for r in updates};new=[selected.get(r['remote'],r) for r in old]
    staging='/data/ai/moss-qwen-case-'+run
    pending=[dict(r,target=r['remote'],remote=staging+('-candidate-SELF.bin' if i==0 else '-'+str(i)+'.json')) for i,r in enumerate(updates)]
    publication=build(args.workspace,args.mount_plan,old,new,pending,'publish',args.out/'publication')
    launcher=build(args.workspace,args.mount_plan,new,new,[],'launch',args.out/'launch',resident=resident)
    plan=dict(completed=True,run_id=run,SELF=image,old_files=old,new_files=new,pending=pending,report=report,
        model_proof=record(args.model_proof),shader_CPU_proof=shader,clock=record(args.clock),
        publication=record(args.out/'publication/plan.private.json'),launch=record(args.out/'launch/plan.private.json'),
        title_launches_maximum=1,initializer_requests=0,automatic_retries=0,ordinary_close_and_original_restore_required=True)
    save(args.out/'plan.private.json',plan)
    if not args.execute:print('Normal model case prepared; PS5 operations=0');return
    state['active_successful_native_case']=dict(plan=record(args.out/'plan.private.json'),run_id=run,phase='publication')
    state['state']='normal_model_case_publication_in_progress';state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    lan=lan_module();publish(lan,pending,publication,args.out/'publication')
    state.update(state='normal_model_case_published_launch_pending',original_restored=False,temporary_installed_SELF=image)
    state['active_successful_native_case']['phase']='launch';state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=execute(lan,launcher,args.out/'launch')
    need(result['operation_calls']==1 and result['app_id']>0,'One accepted ordinary normal launch required')
    state.update(state='normal_model_case_launch_accepted_completion_pending',native_running=True,unknown_completion=True)
    state['active_successful_native_case'].update(phase='native-start-pending',app_id=result['app_id'])
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(launch_accepted=True,app_id=result['app_id'],native_identity_and_completion_pending=True,
                         initializer_requests=0,automatic_retries=0)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','model-proof','clock','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--package',type=Path)
    parser.add_argument('--execute',action='store_true')
    start(parser.parse_args())


if __name__=='__main__':main()
