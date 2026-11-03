#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one finite model audit and require positive retirement before ordinary close."""
import argparse
import json
import re
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import query
from mtp_shadow_host_check import require_profile as require_shadow_host_check,require_target_capture_profile,require_online_profile
from start_success_route import load,need,save
from success_case_control import PHYSICAL,lan_module

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','model-proof','package','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--readiness-pages',type=int,required=True)
    p.add_argument('--direct-staging-proof',type=Path)
    p.add_argument('--cpu-startup-pricing',type=Path)
    p.add_argument('--ordinary-target-pricing',type=Path)
    p.add_argument('--staged-MTP-startup-pricing',type=Path)
    p.add_argument('--collect',action='store_true',help='Continue observing/finalizing the exact accepted owner; never stage or launch again')
    p.add_argument('--quiet-seconds',type=int,default=0,help='Optional host-quiet interval for a separately instrumented component')
    a=p.parse_args();need(0<=a.quiet_seconds<=600,'Finite host-quiet interval required')
    package=load(a.package);effective=package['effective_application_policy'];profile=load(effective['profile']['path'])
    need(effective['kind']=='headless-model-audit' and record(effective['profile']['path'])==effective['profile'] and
         profile['headless_model_audit'] and profile['model_and_GPU_guards_preserved'],'One explicitly compiled headless audit required')
    if profile['headless_audit_kind']=='S1-MTP-shadow':
        require_shadow_host_check(profile)
        need(profile.get('successful_MTP_contract_verified') is True and profile.get('actual_legacy_policy_validator_passed') is True,
             'Successful MTP providers and the actual legacy policy host check must be bound before launch')
        check=profile['legacy_policy_host_check']
        need(record(check['path'])==check and load(check['path'])['actual_legacy_validator_passed'],
             'Exact successful legacy policy host-check receipt required')
    if profile['headless_audit_kind']=='S1-target-hidden-capture-audit':require_target_capture_profile(profile)
    if profile['headless_audit_kind']=='S1-persistent-MTP-online':require_online_profile(profile)
    scope=profile['overrides']['native_headless_model_audit'];count=profile['headless_requests']
    if profile['headless_audit_kind']=='CPU-startup-staging-memory':
        from direct_self_staging import qualification
        need(a.direct_staging_proof and profile.get('unloaded_CPU_fixture') and count==0 and scope['early_return_before_model_source_initialization'] and
            scope['full_original_model_path_linked'] and scope['separate_non_LTO_gate_always_one'] and
            scope['original_reader_floor_and_30_second_total_deadline_unchanged'],
            'The changed CPU-only startup scope requires bounded Direct staging and no model/GPU operation')
        passive=scope.get('passive_before_SELF_settle') is True
        original=scope.get('original_selected_64KiB_reader_after_identical_publication') is True
        need(passive != original,'Exactly one compiled CPU reader scope required')
        if passive:need(scope['maximum_passive_ms']==5000 and scope['additional_pre_read_working_pages']==1152,'Exact passive scope required')
        if original:
            from price_cpu_startup_original_reader import require_pricing
            require_pricing(a.cpu_startup_pricing,a.package)
        qualification(a.direct_staging_proof)
        need(a.cpu_startup_pricing is not None,'Explicit source/geometry-based CPU-only pricing required')
        price=load(a.cpu_startup_pricing)
        need(price['completed'] and price['compiled_CPU_package']==record(a.package) and price['model_GPU_or_source_operations']==0 and
            not price['model_launch_admission_granted'] and price['model_screen_pages_unchanged']==7374 and
            a.readiness_pages==price['selected_CPU_only_prelaunch_screen_pages'],
            'One exact CPU-only package/pricing scope may not reduce the unchanged model screen')
    unloaded=profile.get('unloaded_CPU_fixture') is True
    if a.ordinary_target_pricing:
        from price_ordinary_target_control import require
        pricing=require(a.ordinary_target_pricing,a.package)
        need(profile['headless_audit_kind'] in ('S1-ordinary-target-control','P1-tail-eight') and a.readiness_pages==pricing['selected_readiness_pages'],
             'Only the exact original ordinary target may use its R1-derived pricing')
    if a.staged_MTP_startup_pricing:
        from price_staged_mtp_startup import require
        MTP_pricing=require(a.staged_MTP_startup_pricing,a.package)
        need(not a.ordinary_target_pricing and profile['headless_audit_kind']=='S1-persistent-MTP-online' and
             a.readiness_pages==MTP_pricing['selected_readiness_pages'],
             'Only the corrected finite MTP scope may use measured CPU startup and unchanged live phase admission')
    need(count==scope['requests'] and (count in (1,3) or (count==0 and unloaded and scope['model_loads']==scope['GPU_calls']==0)) and
         scope['HTTP_requests']==scope['VideoOut_starts']==0,'Explicit finite headless request count required')
    if a.collect:
        intent=load(a.out/'intent.private.json');case_plan=load(a.out/'case/plan.private.json');launch=load(a.out/'case/launch/result.private.json')
        need(intent['package']==record(a.package) and intent['native_requests']==count and case_plan['package']==record(a.package) and
             launch['completed'] and launch['operation_calls']==1,'Only the exact already accepted headless owner may be collected')
    else:
        a.out.mkdir(parents=True,exist_ok=False)
        save(a.out/'intent.private.json',dict(package=record(a.package),native_requests=count,HTTP_requests=0,VideoOut_starts=0,
            automatic_retries=0,require_positive_retirement_before_close=True))
    state=load(a.current/'active-console.private.json')
    if a.ordinary_target_pricing:need(pricing['current_boot']==state['current_boot'],'Pricing boot changed')
    if a.staged_MTP_startup_pricing:need(MTP_pricing['current_boot']==state['current_boot'],'Pricing boot changed')
    if a.collect:
        need(state['active_successful_native_case']['run_id']==case_plan['run_id'] and state['native_running'] and not state['original_restored'],
             'The same accepted owner must still be installed; no resubmission is permitted')
    else:
        need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
             'Completed idle current deployment required')
        vm=a.out/'VM-before';vm.mkdir();values=query(lan_module().HOST,vm)
        need(values['boot_before']==values['boot_after']==state['current_boot'] and a.readiness_pages>=values['minimum']+21,
             'Same boot and unchanged original CPU floor required')
        ready=min(values['free_first'],values['free_last'])>=a.readiness_pages
        save(vm/'result.private.json',dict(completed=True,observations=values,selected_readiness_pages=a.readiness_pages,
            application_policy_not_physical_OS_limit=True,may_launch=ready,title_launches=0,GPU_calls=0))
        need(ready,'Headless readiness margin insufficient; no staging or launch')
    def run(name,args,label,early_refusal=None):
        with (a.out/(label+'.private.log')).open('xb') as output:
            child=subprocess.Popen([sys.executable,'-B',str(ROOT/'tools'/name),*map(str,args)],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
            notice=0
            while child.poll() is None:
                if time.monotonic()>=notice:print(json.dumps(dict(phase=name,host_child_running=True)),flush=True);notice=time.monotonic()+30
                time.sleep(1)
        need(child.returncode==0 or (early_refusal is not None and early_refusal.is_file()),
             'Audit stopped; inspect '+str(a.out/(label+'.private.log'))+'; never resubmit a consumed operation')
    common=['--workspace',a.workspace,'--current',a.current,'--mount-plan',a.mount_plan]
    clock=a.out/'clock';case=a.out/'case';closed=a.out/'closed'
    transport=['--direct-staging-proof',a.direct_staging_proof] if a.direct_staging_proof else []
    if not a.collect:
        run('refresh_successful_clock.py',common+['--out',clock,'--execute'],'clock')
        run('run_successful_model_case.py',common+transport+['--model-proof',a.model_proof,'--clock',clock/'clock.private.json',
            '--package',a.package,'--out',case,'--execute'],'start')
    if a.quiet_seconds and not a.collect:
        started=int(time.time()*1000);until=time.monotonic()+a.quiet_seconds
        while time.monotonic()<until:
            print(json.dumps(dict(phase='headless_component_host_quiet',PS5_requests=0,remaining_seconds=max(0,int(until-time.monotonic())))),flush=True)
            time.sleep(min(30,max(0,until-time.monotonic())))
        save(a.out/'quiet-window.private.json',dict(completed=True,start_epoch_ms=started,end_epoch_ms=int(time.time()*1000),PS5_requests=0))
    deadline=time.monotonic()+1800
    used=[int(m[1]) for path in a.out.glob('observe-*.private.log') if (m:=re.fullmatch(r'observe-(\d+)\.private\.log',path.name))]
    poll=max(used,default=-1)+1
    while True:
        run('observe_successful_model_start.py',['--case-plan',case/'plan.private.json'],'observe-'+str(poll),case/'host-early-self-refusal.private.json');poll+=1
        if (case/'host-early-self-refusal.private.json').exists():
            run('close_successful_early_self_refusal.py',common+transport+['--case-plan',case/'plan.private.json','--out',closed],'early-close')
            raise RuntimeError('Known returned CPU SELF refusal closed; no repeated launch')
        if (case/'native.failure.private.json').exists():
            failure=load(case/'native.failure.private.json')
            if failure.get('native_resources_started') is False and failure.get('model_loaded') is False and failure.get('CPU_worker_completion_unknown') is False:
                run('close_successful_model_failure.py',common+transport+['--case-plan',case/'plan.private.json','--out',closed],'pre-GPU-close')
            raise RuntimeError('Native exception; stop without retry or uncertain resource release')
        need(not(case/'native.fatal.private.json').exists(),'Native fatal; retain owner without recovery')
        if (case/'native.result.private.json').exists():break
        need(time.monotonic()<deadline,'Unknown completion; retain owner');time.sleep(3)
    terminal=load(case/'native.result.private.json');first=load(case/'native-first-start.private.json');plan=load(case/'plan.private.json')
    need(terminal['completed'] and terminal['pid']==first['pid'] and terminal['run_id']==plan['run_id'] and
         terminal['kind']==profile['headless_audit_kind'] and terminal['all_model_source_device_owners_positively_retired'] and
         terminal['device_ledger_live_bytes']==0 and terminal['model_loads']==(0 if unloaded else 1) and
         len(terminal['requests'])==count,'Exact positive finite model/source/device retirement required')
    observer=case/'headless-observer';observer.mkdir();(observer/'native.private.bin').write_bytes((case/'native.result.private.json').read_bytes())
    lan=lan_module();remote=PHYSICAL+plan['report'][5:]
    outputs=[('.audit','native.audit.private.json')]
    for ordinal in range(count):
        outputs.extend([('.arm'+str(ordinal)+'.routes','native.arm'+str(ordinal)+'.routes.private.json'),
                        ('.arm'+str(ordinal)+'.result','native.arm'+str(ordinal)+'.result.private.bin')])
    for suffix,target in outputs:(observer/target).write_bytes(lan.web('/fs'+urllib.parse.quote(remote+suffix,safe='/'),4<<20))
    need(load(observer/'native.audit.private.json')==terminal['audit'],'The two completed native audits differ')
    save(observer/'complete.private.json',dict(completed=True,headless_model_audit=True,POSTs=0,automatic_retries=0,
        model_source_GPU_owners_positively_retired=True,native_binding=first))
    run('close_successful_current_model.py',common+transport+['--case-plan',case/'plan.private.json','--out',closed,'--headless-audit'],'close')
    closure=load(closed/'result.private.json')
    need(closure['completed'] and closure['ordinary_exit_observed'] and closure['current_seven_restored_and_native_hashed'] and
         not closure['unknown_completion'],'Positive ordinary current restoration required')
    save(a.out/'result.private.json',dict(completed=True,kind=profile['headless_audit_kind'],native_requests=count,
        terminal=record(observer/'native.private.bin'),audit=record(observer/'native.audit.private.json'),
        closure=record(closed/'result.private.json'),all_counting_and_finite_checks=all(r['counting_quality_passed'] and r['full_F32_finite'] for r in terminal['requests']),
        native_owners=0,unknown_completion=False,HTTP_requests=0,VideoOut_starts=0,automatic_retries=0,production_adopted=False))
    print(json.dumps(dict(completed=True,native_requests=count,kind=profile['headless_audit_kind'],current_restored=True,owners=0)))


if __name__=='__main__':main()
