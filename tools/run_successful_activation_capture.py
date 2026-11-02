#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one finite headless activation scope; close before inspecting its effect."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import query
from start_success_route import load,need,save
from success_case_control import PHYSICAL,lan_module

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','model-proof','package','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--readiness-pages',type=int,required=True,help='Explicit application readiness margin, not a physical OS limit')
    parser.add_argument('--IQ2-fixture',action='store_true',help='Run the distinct unloaded IQ2 component scope instead of activation capture')
    args=parser.parse_args();package=load(args.package);effective=package['effective_application_policy']
    if args.IQ2_fixture:
        profile=load(effective['profile']['path'])
        need(effective['kind']=='Q2-IQ2-fixture' and record(effective['profile']['path'])==effective['profile'] and
             profile['unloaded_GPU_fixture'],'One explicitly compiled unloaded IQ2 program is required')
    else:need(effective['kind']=='Q2-calibration' and effective['overrides']['native_activation_capture']['headless'],
              'One explicitly compiled headless activation program is required')
    args.out.mkdir(parents=True,exist_ok=False);case=args.out/'case';closed=args.out/'closed';clock=args.out/'clock'
    common=['--workspace',args.workspace,'--current',args.current,'--mount-plan',args.mount_plan]
    save(args.out/'intent.private.json',dict(package=record(args.package),maximum_native_requests=0 if args.IQ2_fixture else 1,HTTP_requests=0,
        VideoOut_starts=0,automatic_retries=0,effect_validation_after_positive_retirement_and_ordinary_restore=True))
    state=load(args.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Completed idle state required before readiness observation')
    vm=args.out/'VM-before';vm.mkdir();values=query(lan_module().HOST,vm)
    need(values['boot_before']==values['boot_after']==state['current_boot'] and args.readiness_pages>=values['minimum']+21,
         'The exact boot and unchanged original CPU floor are required')
    ready=min(values['free_first'],values['free_last'])>=args.readiness_pages
    save(vm/'result.private.json',dict(completed=True,observations=values,selected_readiness_pages=args.readiness_pages,
        application_readiness_policy_not_physical_OS_limit=True,may_start_changed_scope=ready,title_launches=0,GPU_calls=0))
    need(ready,'Changed headless calibration readiness margin is insufficient; no staging or launch')
    if args.IQ2_fixture:
        local=profile['component_pack']['local'];remote=PHYSICAL+profile['component_pack']['application_path'][5:]
        need(record(local['path'])==local and remote.startswith(PHYSICAL+'/qwen-runtime/iq2-Up-') and
             local['bytes']<=16<<20,'Exact bounded prepared component pack required')
        lan=lan_module()
        with lan.ftplib.FTP() as ftp:
            ftp.connect(lan.HOST,2121,timeout=20);ftp.login()
            need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled' and ftp.size(remote)==(1<<64)-1,
                 'Raw transfer mode and an absent unique fixture pack are required')
            save(args.out/'pack-upload.once.private.json',dict(local=local,remote=remote,automatic_retries=0))
            with Path(local['path']).open('rb') as stream:reply=ftp.storbinary('STOR '+remote,stream,65536)
            need(reply.startswith(('226 ','250 ')) and ftp.size(remote)==local['bytes'],'Component upload did not complete')
        raw=lan.web('/fs'+urllib.parse.quote(remote,safe='/'),16<<20)
        need(len(raw)==local['bytes'] and hashlib.sha256(raw).hexdigest()==local['sha256'],'Whole uploaded component digest differs')
        save(args.out/'pack-readback.private.json',dict(completed=True,remote=remote,bytes=len(raw),sha256=local['sha256']))
    def script(name,arguments,label):
        with (args.out/(label+'.private.log')).open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/'tools'/name),*map(str,arguments)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            notice=0
            while child.poll() is None:
                if time.monotonic()>=notice:
                    print(json.dumps(dict(phase=name,host_child_running=True)),flush=True);notice=time.monotonic()+30
                time.sleep(1)
        return child.returncode
    need(script('refresh_successful_clock.py',common+['--out',clock,'--execute'],'clock')==0,'Fresh clock failed; stop without replay')
    need(script('run_successful_model_case.py',common+['--model-proof',args.model_proof,'--clock',clock/'clock.private.json',
        '--package',args.package,'--out',case,'--execute'],'start')==0,'Startup submission stopped; never resubmit')
    if args.IQ2_fixture:
        # Numerical/model capture may poll; a microbenchmark must not compete
        # with host-triggered console HTTP/FTP/journal reads while measuring.
        quiet_start=int(time.time()*1000);until=time.monotonic()+420
        while time.monotonic()<until:
            print(json.dumps(dict(phase='unloaded_component_quiet_window',PS5_requests=0,
                remaining_seconds=max(0,int(until-time.monotonic())))),flush=True)
            time.sleep(min(30,max(0,until-time.monotonic())))
        save(args.out/'quiet-window.private.json',dict(completed=True,start_epoch_ms=quiet_start,end_epoch_ms=int(time.time()*1000),PS5_requests=0))
    deadline=time.monotonic()+1800;poll=0
    while True:
        code=script('observe_successful_model_start.py',['--case-plan',case/'plan.private.json'],'read-'+str(poll));poll+=1
        if (case/'host-early-self-refusal.private.json').exists():
            need(script('close_successful_early_self_refusal.py',common+['--case-plan',case/'plan.private.json','--out',closed],'early-close')==0,
                 'Known CPU refusal close did not positively finish; no retry')
            raise RuntimeError('Returned pre-main CPU refusal closed and current restored; no repeated launch')
        need(code==0,'Read-only observation failed; stop without replay')
        if (case/'native.failure.private.json').exists():
            failure=load(case/'native.failure.private.json')
            if failure.get('native_resources_started') is False and failure.get('model_loaded') is False and failure.get('CPU_worker_completion_unknown') is False:
                need(script('close_successful_model_failure.py',common+['--case-plan',case/'plan.private.json','--out',closed],'pre-GPU-close')==0,
                     'Known pre-GPU refusal close did not finish')
            raise RuntimeError('Native failure observed; stop without retry')
        need(not(case/'native.fatal.private.json').exists(),'Native fatal; retain owner without recovery')
        if (case/'native.result.private.json').exists():break
        need(time.monotonic()<deadline,'Completion deadline expired; retain owner without replay');time.sleep(3)
    plan=load(case/'plan.private.json');first=load(case/'native-first-start.private.json');terminal=load(case/'native.result.private.json')
    need(terminal['completed'] and terminal['pid']==first['pid'] and terminal['run_id']==plan['run_id'] and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0,
         'Positive original model/source/device retirement is required before close')
    lan=lan_module();remote=PHYSICAL+plan['report'][5:];observer=case/'headless-observer';observer.mkdir()
    (observer/'native.private.bin').write_bytes((case/'native.result.private.json').read_bytes())
    outputs=[('.IQ2-component','native.IQ2-component.private.json')] if args.IQ2_fixture else \
        [('.arm0.result','native.arm0.result.private.bin'),('.arm0.routes','native.arm0.routes.private.json'),('.activation-capture','activation-capture.private.json')]
    for suffix,target in outputs:
        raw=lan.web('/fs'+urllib.parse.quote(remote+suffix,safe='/'),4<<20);(observer/target).write_bytes(raw)
    save(observer/'complete.private.json',dict(completed=True,headless_calibration=not args.IQ2_fixture,unloaded_IQ2_fixture=bool(args.IQ2_fixture),POSTs=0,automatic_retries=0,
        model_source_GPU_owners_positively_retired=True,native_binding=first))
    close_mode='--IQ2-fixture' if args.IQ2_fixture else '--headless-calibration'
    need(script('close_successful_current_model.py',common+['--case-plan',case/'plan.private.json','--out',closed,close_mode],'close')==0,
         'Ordinary close/restoration did not positively finish; no retry')
    closure=load(closed/'result.private.json');need(closure['completed'] and closure['current_seven_restored_and_native_hashed'] and
        closure['ordinary_exit_observed'] and not closure['unknown_completion'],'Positive ordinary restoration is required')
    if args.IQ2_fixture:
        component=load(observer/'native.IQ2-component.private.json')
        qualified=component['all_outputs_reference_valid'] and len(component['cases'])==6 and component['GPU_graphs']==72
        quiet=load(args.out/'quiet-window.private.json');uncertainty=component['clock_uncertainty_ms']
        quiet_qualified=component['clock_calibrated'] and component['started_epoch_ms']-uncertainty>=quiet['start_epoch_ms'] and \
            component['completed_epoch_ms']+uncertainty<=quiet['end_epoch_ms']
        save(args.out/'result.private.json',dict(completed=True,case=record(case/'plan.private.json'),closure=record(closed/'result.private.json'),
            component=record(observer/'native.IQ2-component.private.json'),native_operator_numerics_qualified=qualified,
            component_timing_window_free_of_host_PS5_requests=quiet_qualified,quiet_window=record(args.out/'quiet-window.private.json'),
            matched_component_timing_analysis_pending=True,full_model_quality_or_speed_qualified=False,model_loads=0,automatic_retries=0,production_adopted=False))
        print(json.dumps(dict(completed=True,model_loads=0,GPU_graphs=component['GPU_graphs'],native_operator_numerics_qualified=qualified,current_restored=True)),flush=True)
        return
    capture=load(observer/'activation-capture.private.json')
    need(capture['completed'] and not capture['diagnostic_failed'] and capture['full_native_SHA256_and_EOF_verified'] and
        capture['all_file_calls_returned'] and not capture['scratch_retained_until_ordinary_close'] and
        1<=capture['evaluations']<=33 and capture['records']==96*capture['evaluations'] and
        16384<capture['bytes']<=256<<20,'Capture effect failed; current is already restored')
    need(capture['path']==plan['report']+'.activation-samples.bin','Exact bound raw stream path required')
    target=args.out/'activation-samples.private.bin';digest=hashlib.sha256();count=0
    url='http://'+lan.HOST+':8080/fs'+urllib.parse.quote(PHYSICAL+capture['path'][5:],safe='/')
    with lan.OPENER.open(url,timeout=30) as response,target.open('xb') as stream:
        while block:=response.read(1<<20):
            count+=len(block);need(count<=capture['bytes'],'Capture exceeds the exact sealed length');stream.write(block);digest.update(block)
    need(count==capture['bytes'] and digest.hexdigest()==capture['sha256'],'Independent host whole SHA256 or EOF differs')
    save(args.out/'result.private.json',dict(completed=True,case=record(case/'plan.private.json'),closure=record(closed/'result.private.json'),
        capture=record(observer/'activation-capture.private.json'),raw=record(target),native_and_host_whole_SHA256_equal=True,
        native_requests=1,HTTP_requests=0,VideoOut_starts=0,automatic_retries=0,importance_accumulation_pending=True,
        performance_timings_usable=False,production_adopted=False))
    print(json.dumps(dict(completed=True,native_requests=1,records=capture['records'],raw_bytes=count,current_restored=True)),flush=True)


if __name__=='__main__':main()
