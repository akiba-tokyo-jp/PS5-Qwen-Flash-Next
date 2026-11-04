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
    parser.add_argument('--resume-published-component',action='store_true',help='Continue an unlaunched scope after its prepared CPU publication positively completed')
    parser.add_argument('--published-component',type=Path,help='Reuse an existing sealed immutable pack with exactly the same bytes; native startup hashes it again')
    parser.add_argument('--direct-staging-proof',type=Path)
    parser.add_argument('--model-free-pricing',type=Path)
    args=parser.parse_args();package=load(args.package);effective=package['effective_application_policy']
    need(not(args.resume_published_component and args.published_component),'One component publication source required')
    if args.IQ2_fixture:
        profile=load(effective['profile']['path'])
        need(effective['kind']=='Q2-IQ2-fixture' and record(effective['profile']['path'])==effective['profile'] and
             profile['unloaded_GPU_fixture'],'One explicitly compiled unloaded IQ2 program is required')
        if (profile['overrides']['native_IQ2_fixture'].get('F32_shader_arithmetic_explicit') or
                profile['overrides']['native_IQ2_fixture'].get('F16_storage_FP32_accumulation') or
                profile['overrides']['native_IQ2_fixture'].get('MMVQ_decode_FP32_accumulation')):
            from price_unloaded_iq2_startup import require_pricing
            need(args.direct_staging_proof and args.model_free_pricing,'Exact Direct transport and source-bound model-free pricing required')
            price=require_pricing(args.model_free_pricing,args.package)
            need(args.readiness_pages==max(7374,price['selected_model_free_readiness_pages']),
                 'Preserve the ordinary7374-page floor and any higher source-bound component price')
    else:need(effective['kind']=='Q2-calibration' and effective['overrides']['native_activation_capture']['headless'],
              'One explicitly compiled headless activation program is required')
    case=args.out/'case';closed=args.out/'closed';clock=args.out/'clock'
    if args.resume_published_component:
        need(args.IQ2_fixture and not case.exists() and not clock.exists() and
             load(args.out/'intent.private.json')['package']==record(args.package),
             'Only the exact still-unlaunched scope can continue after a completed component publication')
        publication=args.out/'component-publication';published=load(publication/'result.private.json')
        need(published['completed'] and published['profile']==effective['profile'] and published['current_seven_unchanged_and_native_hashed'],
             'The exact positive new-only publication must already be complete')
        save(args.out/'resume-after-published-component.private.json',dict(completed=True,publication=record(publication/'result.private.json'),
            native_launch_calls_before_resume=0,component_publication_resubmitted=False))
    else:args.out.mkdir(parents=True,exist_ok=False)
    if args.published_component:
        published=load(args.published_component)
        need(args.IQ2_fixture and published['completed'] and published['whole_physical_and_alias_SHA256_EOF'] and
             published['helper_retired'] and published['pack']==profile['component_pack']['local'],
             'Only the exact previously sealed immutable pack may be reused')
        publication=args.published_component.parent
        save(args.out/'reused-component-publication.private.json',dict(completed=True,publication=record(args.published_component),
            pack=published['pack'],new_publication_calls=0,native_full_pack_hash_required=True))
    common=['--workspace',args.workspace,'--current',args.current,'--mount-plan',args.mount_plan]
    transport=['--direct-staging-proof',args.direct_staging_proof] if args.direct_staging_proof else []
    if not args.resume_published_component:
        save(args.out/'intent.private.json',dict(package=record(args.package),maximum_native_requests=0 if args.IQ2_fixture else 1,HTTP_requests=0,
            VideoOut_starts=0,automatic_retries=0,effect_validation_after_positive_retirement_and_ordinary_restore=True))
    state=load(args.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Completed idle state required before readiness observation')
    vm=args.out/'VM-before'
    if args.resume_published_component:values=load(vm/'result.private.json')['observations']
    else:vm.mkdir();values=query(lan_module().HOST,vm)
    need(values['boot_before']==values['boot_after']==state['current_boot'] and args.readiness_pages>=values['minimum']+21,
         'The exact boot and unchanged original CPU floor are required')
    ready=min(values['free_first'],values['free_last'])>=args.readiness_pages
    if not args.resume_published_component:
        save(vm/'result.private.json',dict(completed=True,observations=values,selected_readiness_pages=args.readiness_pages,
            application_readiness_policy_not_physical_OS_limit=True,may_start_changed_scope=ready,title_launches=0,GPU_calls=0))
    need(ready,'Changed headless calibration readiness margin is insufficient; no staging or launch')
    def script(name,arguments,label):
        with (args.out/(label+'.private.log')).open('xb') as stream:
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/'tools'/name),*map(str,arguments)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            notice=0
            while child.poll() is None:
                if time.monotonic()>=notice:
                    print(json.dumps(dict(phase=name,host_child_running=True)),flush=True);notice=time.monotonic()+30
                time.sleep(1)
        return child.returncode
    if args.IQ2_fixture and not args.resume_published_component and not args.published_component:
        publication=args.out/'component-publication'
        need(script('publish_native_component_pack.py',common+['--profile',effective['profile']['path'],'--out',publication],
                    'publish-component')==0,'Component publication stopped; collect its same journal if needed, never resubmit it')
        need(load(publication/'result.private.json')['completed'],'Positive immutable component publication required')
    need(script('refresh_successful_clock.py',common+['--out',clock,'--execute'],'clock')==0,'Fresh clock failed; stop without replay')
    need(script('run_successful_model_case.py',common+transport+['--model-proof',args.model_proof,'--clock',clock/'clock.private.json',
        '--package',args.package,'--out',case,'--execute'],'start')==0,'Startup submission stopped; never resubmit')
    if args.IQ2_fixture:
        # Numerical/model capture may poll; a microbenchmark must not compete
        # with host-triggered console HTTP/FTP/journal reads while measuring.
        qualification_only=profile['overrides']['native_IQ2_fixture'].get('qualification_only') is True
        quiet_start=int(time.time()*1000);until=time.monotonic()+(0 if qualification_only else 420)
        while time.monotonic()<until:
            print(json.dumps(dict(phase='unloaded_component_quiet_window',PS5_requests=0,
                remaining_seconds=max(0,int(until-time.monotonic())))),flush=True)
            time.sleep(min(30,max(0,until-time.monotonic())))
        save(args.out/'quiet-window.private.json',dict(completed=True,start_epoch_ms=quiet_start,end_epoch_ms=int(time.time()*1000),PS5_requests=0))
    deadline=time.monotonic()+1800;poll=0
    while True:
        code=script('observe_successful_model_start.py',['--case-plan',case/'plan.private.json'],'read-'+str(poll));poll+=1
        if (case/'host-early-self-refusal.private.json').exists():
            need(script('close_successful_early_self_refusal.py',common+transport+['--case-plan',case/'plan.private.json','--out',closed],'early-close')==0,
                 'Known CPU refusal close did not positively finish; no retry')
            raise RuntimeError('Returned pre-main CPU refusal closed and current restored; no repeated launch')
        need(code==0,'Read-only observation failed; stop without replay')
        if (case/'native.failure.private.json').exists():
            failure=load(case/'native.failure.private.json')
            if failure.get('native_resources_started') is False and failure.get('model_loaded') is False and failure.get('CPU_worker_completion_unknown') is False:
                need(script('close_successful_model_failure.py',common+transport+['--case-plan',case/'plan.private.json','--out',closed],'pre-GPU-close')==0,
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
    need(script('close_successful_current_model.py',common+transport+['--case-plan',case/'plan.private.json','--out',closed,close_mode],'close')==0,
         'Ordinary close/restoration did not positively finish; no retry')
    closure=load(closed/'result.private.json');need(closure['completed'] and closure['current_seven_restored_and_native_hashed'] and
        closure['ordinary_exit_observed'] and not closure['unknown_completion'],'Positive ordinary restoration is required')
    if args.IQ2_fixture:
        component=load(observer/'native.IQ2-component.private.json')
        scope=profile['overrides']['native_IQ2_fixture']
        qualified=component['all_outputs_reference_valid'] and len(component['cases'])==scope['cases'] and component['GPU_graphs']==scope['maximum_GPU_graphs']
        quiet=load(args.out/'quiet-window.private.json');uncertainty=component['clock_uncertainty_ms']
        quiet_qualified=not qualification_only and component['clock_calibrated'] and component['started_epoch_ms']-uncertainty>=quiet['start_epoch_ms'] and \
            component['completed_epoch_ms']+uncertainty<=quiet['end_epoch_ms']
        save(args.out/'result.private.json',dict(completed=True,case=record(case/'plan.private.json'),closure=record(closed/'result.private.json'),
            component=record(observer/'native.IQ2-component.private.json'),native_operator_numerics_qualified=qualified,
            component_publication=record(publication/'result.private.json'),
            component_timing_window_free_of_host_PS5_requests=quiet_qualified,quiet_window=record(args.out/'quiet-window.private.json'),
            matched_component_timing_analysis_pending=not qualification_only,full_model_quality_or_speed_qualified=False,model_loads=0,automatic_retries=0,production_adopted=False))
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
