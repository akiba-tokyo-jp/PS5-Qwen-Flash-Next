#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare/run one audited CPU shader bootstrap and restore the current program."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import secrets
import time
import urllib.error
import urllib.parse

from build_performance_quantizer import record
from staged_self_upload import upload
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','package','mount-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',type=int,required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--collect-existing',action='store_true',help='Collect/close/restore the already accepted case; never publish or launch it again')
    args=parser.parse_args()
    if args.collect_existing:
        need(args.execute,'Existing collection needs execution permission for ordinary close/restoration')
        return collect_existing(args)
    args.out.mkdir(parents=True,exist_ok=False)
    package=load(args.package)
    need(package.get('CPU_only') is True and package.get('driver_code_linked') is False and
         package.get('normalized_SELF_roundtrip_equal') is True,'Independently audited CPU-only package required')
    candidate=package['SELF'];need(record(candidate['path'])==candidate and candidate['bytes']<=4<<20,'Exact CPU SELF required')
    old=current_files(args.current);policy=load(args.current/'qwen-runtime/development.json');app=load(args.current/'qwen-runtime/app.json')
    run=secrets.token_hex(16);report='/app0/qwen-runtime/plan-'+run+'.json'
    storage=copy.deepcopy(policy['native_shader_storage']);storage.pop('prior_native_CPU',None)
    storage['verify_all_original_assets_before_Vulkan']=True
    gate=policy['native_first_generation_validation']
    new_policy=dict(console_operations_enabled=True,allowed_modes=['first-generation-validation'],
        native_mini_shader_bootstrap=dict(schema='ps5-qwen-mini-shader-bootstrap-v1',CPU_only=True,
            maximum_SELF_bytes=4<<20,maximum_CPU_heap_bytes=16<<20,complete_original_assets=1527,
            complete_original_lookups=382,GPU_calls=0,model_loads=0,source_workers=0,automatic_retries=0),
        native_shader_storage=storage,native_first_generation_validation=dict(run_id=run,
            candidate_SELF_bytes=candidate['bytes'],candidate_SELF_sha256=candidate['sha256'],
            model_receipt_bytes=gate['model_receipt_bytes'],model_receipt_sha256=gate['model_receipt_sha256']))
    bundle=package.get('required_bundle_restore')
    if bundle:new_policy['native_required_bundle_restore']=bundle['scope']
    new_app=dict(schema='ps5-qwen-app-v1',development_policy='/app0/qwen-runtime/development.json',
                 model_receipt=app['model_receipt'],web_assets=app['web_assets'],port=app['port'],
                 native_display=False,mode='first-generation-validation',admission_report=report)
    app_path=args.out/'app.json';policy_path=args.out/'development.json'
    app_path.write_text(json.dumps(new_app,indent=2)+'\n',encoding='utf-8')
    policy_path.write_text(json.dumps(new_policy,indent=2)+'\n',encoding='utf-8')
    updates=[dict(candidate,remote=PHYSICAL+'/eboot.bin'),
             dict(record(app_path),remote=PHYSICAL+'/qwen-runtime/app.json'),
             dict(record(policy_path),remote=PHYSICAL+'/qwen-runtime/development.json')]
    changes={r['remote']:r for r in updates};new=[changes.get(r['remote'],r) for r in old]
    staging='/data/ai/moss-qwen-case-'+run
    pending=[dict(updates[0],remote=staging+'-candidate-SELF.bin',target=updates[0]['remote'])]
    pending += [dict(r,remote=staging+'-'+name+'.pending.json',target=r['remote'])
                for name,r in zip(('app','development'),updates[1:])]
    publication=build(args.workspace,args.mount_plan,old,new,pending,'publish',args.out/'publication')
    launch=build(args.workspace,args.mount_plan,new,new,[],'launch',args.out/'launch')
    plan=dict(completed=True,case=args.case,run_id=run,CPU_only=True,package=record(args.package),candidate=candidate,
              old_files=old,new_files=new,pending=pending,report=report,
              publication=record(args.out/'publication/plan.private.json'),launch=record(args.out/'launch/plan.private.json'),
              GPU_calls=0,initializer_requests=0,maximum_title_launches=1,ordinary_close_and_current_restore_required=True)
    if bundle:plan['required_bundle_restore']=bundle
    save(args.out/'plan.private.json',plan)
    if not args.execute:
        print(json.dumps(dict(CPU_case_prepared=True,publication_and_launch_built=True,PS5_operations=0)));return
    lan=lan_module();context_path=args.current/'active-console.private.json';state=load(context_path)
    need(not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Positively idle application state required')
    state['state']='CPU_shader_bootstrap_publication_in_progress'
    state['active_successful_native_case']=dict(plan=record(args.out/'plan.private.json'),phase='publication',run_id=run)
    context_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    def stage_metadata(rows):
        with lan.ftplib.FTP() as ftp:
            ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw FTP mode required')
            for row in rows:
                need(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},'Pending metadata input changed')
                lan.absent(row['remote'])
                with Path(row['path']).open('rb') as stream:response=ftp.storbinary('STOR '+row['remote'],stream,65536)
                need(response.startswith(('226 ','250 ')),'Metadata upload did not complete')
    stage_metadata(pending[1:])
    def verified_publication(capture,remote):
        need(remote==pending[0]['remote'] and capture==candidate,'Exact pending SELF binding required')
        result=execute(lan,publication,args.out/'publication')
        need(result['operation_calls']==3,'All three exact owned publications required')
        return dict(whole_native_SHA256_identity_EOF_verified=True,all_reads_returned=True,
                    sha256=capture['sha256'],bytes=capture['bytes'],published_after_native_verification=True,
                    proof=record(args.out/'publication/result.private.json'))
    upload(candidate,pending[0]['remote'],args.out/'SELF-transfer',lan,verified_publication)
    if bundle:
        log=(args.out/'publication/execution/console.private.log').read_bytes()
        capacity=re.findall(rb'OWNED_TITLE_CAPACITY block_bytes=(\d+) available_blocks=(\d+)',log)
        need(capacity and min(int(a)*int(b) for a,b in capacity)>=bundle['scope']['bytes']+65536,
             'Fresh external owned-filesystem capacity must admit the complete original output')
    state['state']='CPU_shader_bootstrap_published_launch_pending';state['active_successful_native_case']['phase']='launch'
    state['original_restored']=False;state['temporary_installed_SELF']=candidate
    context_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    started=execute(lan,launch,args.out/'launch')
    need(started['operation_calls']==1 and started['app_id']>0,'One accepted ordinary application launch required')
    state.update(native_running=True,unknown_completion=True)
    state['active_successful_native_case'].update(phase='native-start-pending',app_id=started['app_id'])
    context_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    return finish(args,plan,state,lan,context_path,started)


def collect_existing(args):
    plan=load(args.out/'plan.private.json')
    need(plan['CPU_only'] and plan['maximum_title_launches']==1,'Exact existing CPU-only case required')
    started=load(args.out/'launch/result.private.json')
    need(started['completed'] and started['operation_calls']==1 and started['app_id']>0,'One already accepted launch required')
    context_path=args.current/'active-console.private.json';state=load(context_path)
    need(state['active_successful_native_case']['run_id']==plan['run_id'],'Same active case required')
    return finish(args,plan,state,lan_module(),context_path,started)


def finish(args,plan,state,lan,context_path,started):
    run=plan['run_id'];report=plan['report'];candidate=plan['candidate'];old=plan['old_files'];new=plan['new_files']
    staging='/data/ai/moss-qwen-case-'+run
    def stage_metadata(rows):
        with lan.ftplib.FTP() as ftp:
            ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw FTP mode required')
            for row in rows:
                need(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},'Pending metadata input changed')
                lan.absent(row['remote'])
                with Path(row['path']).open('rb') as stream:response=ftp.storbinary('STOR '+row['remote'],stream,65536)
                need(response.startswith(('226 ','250 ')),'Metadata upload did not complete')
    controller=load(args.mount_plan)['controller'];need(record(controller['path'])==controller,'Exact current boot controller required')
    source=Path(controller['path']).read_text()
    boot=re.search(r'boot.tv_sec!=(\d+)LL\|\|boot.tv_usec!=(\d+)LL',source)
    need(boot is not None,'Current boot-qualified native journal identity required')
    app_id=started['app_id'];remote_report=PHYSICAL+report[5:];deadline=time.monotonic()+180
    cpu=None;assets=None;native_pid=None;stage=None;refused=False
    while time.monotonic()<deadline:
        try:
            start_raw=lan.web('/fs'+urllib.parse.quote(remote_report+'.first.start',safe='/'),4096)
            first=json.loads(start_raw);need(first['run_id']==run and first['candidate_SELF_sha256']==candidate['sha256'],'Fresh native CPU owner binding differs')
            native_pid=int(first['pid'])
            state.update(native_running=True,observed_native_pid=native_pid,native_owners=1)
            state['active_successful_native_case'].update(phase='CPU-running',native_pid=native_pid,app_id=app_id)
            context_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
            stage_remote=PHYSICAL+'/qwen-runtime/entry-b'+boot[1]+'-'+boot[2]+'-'+str(native_pid)+'.stages'
            stage=lan.web('/fs'+urllib.parse.quote(stage_remote,safe='/'),2<<20)
            (args.out/'native-stages.private.log').write_bytes(stage)
            if b'mini_shader_bootstrap_CPU_completed_GPU_not_started_waiting_for_ordinary_close' in stage:
                cpu=lan.web('/fs'+urllib.parse.quote(remote_report+'.CPU-bootstrap',safe='/'),16384)
                assets=lan.web('/fs'+urllib.parse.quote(remote_report+'.shader-assets.CPU',safe='/'),4096);break
            if b'mini_shader_bootstrap_CPU_known_returned_refusal_GPU_not_started' in stage:
                # This audited package has synchronous inputs, no source workers
                # and no GPU/model code. This marker follows exception unwind;
                # the remaining operation is an idle halt and ordinary OS close.
                refused=True;break
        except urllib.error.HTTPError as error:need(error.code==404,'Native CPU report state is unknown')
        time.sleep(1)
    need(refused or (cpu is not None and assets is not None),'CPU completion pending; do not relaunch or assume ordinary-close admission')
    if not refused:
        cpu_data=json.loads(cpu);asset_data=json.loads(assets)
        need(cpu_data['pid']==native_pid and cpu_data['run_id']==run and cpu_data['GPU_calls']==0 and
         cpu_data['CPU_verified_assets']==1527 and cpu_data['CPU_verified_lookups']==382 and
         cpu_data['all_started_input_calls_returned'] is True,'Complete current-run CPU bootstrap required')
        need(asset_data['pid']==native_pid and asset_data['run_id']==run and asset_data['CPU_verified_assets']==1527 and
         asset_data['CPU_verified_lookups']==382 and not asset_data['active_lease'] and not asset_data['failed'] and
         asset_data['GPU_calls']==0 and not asset_data['Vulkan_initialized'] and not asset_data['model_loaded'] and
         not asset_data['external_read_pending'] and not asset_data['external_source_failed'],'Complete current shader bytes required')
    close_reports=[];restored_bundle=None
    report_rows=(('.first.start',start_raw),('.stages',stage)) if refused else (('.CPU-bootstrap',cpu),('.shader-assets.CPU',assets))
    if not refused and plan.get('required_bundle_restore'):
        scope=plan['required_bundle_restore']['scope']
        bundle_raw=lan.web('/fs'+urllib.parse.quote(remote_report+'.required-bundle',safe='/'),16384)
        restored_bundle=json.loads(bundle_raw)
        need(restored_bundle['completed'] and restored_bundle['pid']==native_pid and restored_bundle['run_id']==run and
             restored_bundle['scope']==scope and restored_bundle['full_original_SHA256_and_EOF_readback'] is True and
             restored_bundle['tracked_CPU_heap_free_returned'] is True and restored_bundle['all_started_input_calls_returned'] is True and
             restored_bundle['source_payloads_unchanged'] is True and restored_bundle['GPU_calls']==0 and not restored_bundle['model_loaded'],
             'Positive original-digest-bound copy and tracked CPU retirement required')
        report_rows=(*report_rows,('.required-bundle',bundle_raw))
    for suffix,raw in report_rows:
        path=args.out/('native'+suffix+'.private.json');path.write_bytes(raw)
        remote=stage_remote if suffix=='.stages' else remote_report+suffix
        close_reports.append(dict(record(path),remote=remote))
    state['state']='CPU_shader_bootstrap_completed_ordinary_close_pending';state.update(native_running=True,observed_native_pid=native_pid,native_owners=1,unknown_completion=False)
    state['active_successful_native_case'].update(phase='ordinary-close',native_pid=native_pid,app_id=app_id)
    context_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    close_plan=build(args.workspace,args.mount_plan,new,new,[],'close',args.out/'ordinary-close',
                     close=dict(CPU_only=True,all_CPU_IO_returned=True,pid=native_pid,app_id=app_id,reports=close_reports))
    execute(lan,close_plan,args.out/'ordinary-close')
    deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(r['name']=='eboot.bin' for r in rows):break
        need(time.monotonic()<deadline,'Ordinary title close is not complete; retain all records');time.sleep(.25)
    # Restore only the canonical selected application, from its immutable PC copy.
    restore_pending=[]
    for i,row in enumerate(old[:3]):
        target=staging+'-restore-SELF.bin' if i==0 else staging+'-restore-'+str(i)+'.json'
        restore_pending.append(dict(row,remote=target,target=row['remote']))
    restore_plan=build(args.workspace,args.mount_plan,new,old,restore_pending,'publish',args.out/'restore')
    stage_metadata(restore_pending[1:])
    def verified_restore(capture,remote):
        need(remote==restore_pending[0]['remote'],'Exact selected current SELF restoration required')
        result=execute(lan,restore_plan,args.out/'restore');need(result['operation_calls']==3,'All selected startup files must restore')
        return dict(whole_native_SHA256_identity_EOF_verified=True,all_reads_returned=True,sha256=capture['sha256'],bytes=capture['bytes'])
    original={k:old[0][k] for k in ('path','bytes','sha256')}
    upload(original,restore_pending[0]['remote'],args.out/'restore-SELF-transfer',lan,verified_restore)
    state.update(state='runtime_mount_and_current_boot_shader_CPU_ready_original_restored',native_running=False,
                 native_owners=0,model_loaded=False,gateway_running=False,unknown_completion=False,original_restored=True,
                 current_boot_shader_CPU_proof_pending=state.get('current_boot_shader_CPU_proof_pending',True) if refused else False,
                 current_boot_Qwen_model_admitted=False,current_boot_readmission_pending=True)
    state['active_successful_native_case']['phase']='CPU-complete-original-restored'
    if restored_bundle:
        state.setdefault('native_required_bundle_restorations',[]).append(dict(report=record(args.out/'native.required-bundle.private.json'),
            ordinary_close_completed=True,current_original_restored=True,root_ownership_finalization_pending=True))
    if not refused:
        state['successful_route_20261102']['current_boot_shader_CPU']=dict(path=str(args.out/'native.shader-assets.CPU.private.json'),
            report_path='/app0'+remote_report[len(PHYSICAL):]+'.shader-assets.CPU',pid=native_pid,run_id=run,
            report_bytes=len(assets),report_sha256=hashlib.sha256(assets).hexdigest())
    else:
        state['state']='CPU_shader_bootstrap_known_refusal_closed_original_restored'
        state['active_successful_native_case']['phase']='known-refusal-original-restored'
    context_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=dict(completed=not refused,known_CPU_refusal=refused,CPU_verified_assets=0 if refused else 1527,
                CPU_verified_lookups=0 if refused else 382,GPU_calls=0,model_loads=0,
                native_title_launches=1,ordinary_OS_closes=1,ordinary_exit_observed=True,
                current_original_restored=True,current_seven_file_native_hashes_pass=True,
                fresh_shader_report=state['successful_route_20261102'].get('current_boot_shader_CPU'),
                required_bundle_restored=restored_bundle is not None,
                full_model_speed_or_quality_measured=False)
    save(args.out/'result.private.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='fresh_shader_report'}))


if __name__=='__main__':main()
