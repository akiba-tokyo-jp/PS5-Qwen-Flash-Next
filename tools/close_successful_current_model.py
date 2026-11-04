#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ordinarily close a positively retired current model and restore selected files."""
import argparse
import json
from pathlib import Path
import time
import urllib.parse

from build_performance_quantizer import record
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL


def completed_terminal_journal(stages,CPU_startup=False):
    marker=(b'CPU_startup_memory_completed_waiting_for_ordinary_close' if CPU_startup else
            b'resident_additional_completed_waiting_for_ordinary_close')
    if marker not in stages:return False
    if CPU_startup:
        need(stages.splitlines()[-1]==marker and stages.count(marker)==1 and
             b'early_SELF_whole_Direct_hash_completed_at_main_entry_after_CXX' in stages and
             all(value not in stages for value in (b'model_mapping_',b'native_GPU_initialize',b'inference_before_')),
             'Only the exact parked CPU completion before model/source/GPU work is admitted')
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--headless-calibration',action='store_true')
    parser.add_argument('--IQ2-fixture',action='store_true')
    parser.add_argument('--headless-audit',action='store_true')
    parser.add_argument('--direct-staging-proof',type=Path)
    parser.add_argument('--prior-refused-close',type=Path,
        help='An exited zero-operation helper whose headless route proof used the wrong arm')
    args=parser.parse_args();need(sum((args.headless_calibration,args.IQ2_fixture,args.headless_audit))<=1,'One explicit completed scope is required')
    finite=args.headless_calibration or args.IQ2_fixture or args.headless_audit
    case=load(args.case_plan);observer=args.case_plan.parent/('headless-observer' if finite else 'passive-observer')
    completed=load(observer/'complete.private.json');terminal_path=observer/'native.private.bin';terminal=load(terminal_path)
    first=load(args.case_plan.parent/'native-first-start.private.json');launch=load(args.case_plan.parent/'launch/result.private.json')
    count=0 if args.IQ2_fixture else (1 if args.headless_calibration else 3)
    unloaded_CPU=False
    if args.headless_audit:
        package=load(case['package']['path']);effective=package['effective_application_policy'];profile=load(effective['profile']['path'])
        count=profile['headless_requests']
        unloaded_CPU=profile.get('unloaded_CPU_fixture') is True
        need(record(effective['profile']['path'])==effective['profile'] and effective['kind']=='headless-model-audit' and
             profile['headless_model_audit'] and profile['model_and_GPU_guards_preserved'] and
             (count in (1,3) or (count==0 and unloaded_CPU and profile['headless_audit_kind'] in ('I1-span-fixture','CPU-Direct-readmission','CPU-startup-staging-memory'))) and
             terminal['kind']==profile['headless_audit_kind'] and terminal['model_loads']==(0 if unloaded_CPU else 1) and
             completed['headless_model_audit'] and terminal['audit']==load(observer/'native.audit.private.json'),
             'One explicitly compiled completed headless model audit is required')
        if unloaded_CPU:
            need(terminal['audit']['completed'] and terminal['audit']['source_descriptor_worker_and_scratch_retired'] and
                 terminal['audit']['model_loads']==terminal['audit']['GPU_calls']==0,
                 'Positive unloaded CPU source/worker/allocation retirement required')
    if args.headless_calibration:
        package=load(case['package']['path']);effective=package['effective_application_policy'];profile=load(effective['profile']['path'])
        need(record(effective['profile']['path'])==effective['profile'] and effective['kind']=='Q2-calibration' and
             profile['headless_calibration'] and effective['overrides']['native_activation_capture']['headless'] and
             terminal['kind']=='Q2-headless-calibration' and completed['headless_calibration'],
             'Only an explicitly compiled headless calibration contract is admitted')
    if args.IQ2_fixture:
        package=load(case['package']['path']);effective=package['effective_application_policy'];profile=load(effective['profile']['path'])
        component=terminal['component']
        scope=profile['overrides']['native_IQ2_fixture'];case_bound=scope['cases'];graph_bound=scope['maximum_GPU_graphs']
        arithmetic_only=(scope.get('qualification_only') is True and
                         ((scope.get('F16_storage_FP32_accumulation') is True and
                           scope.get('widths')==[30,32] and component.get('F16_storage_FP32_accumulation') is True) or
                          (scope.get('MMVQ_decode_FP32_accumulation') is True and scope.get('widths')==[1,2] and
                           scope.get('backend_environment')=={} and scope.get('synthetic_inputs_exactly_Q8_1') is True and
                           component.get('MMVQ_decode_FP32_accumulation') is True and
                           component.get('vector_MMVQ_disabled') is False)) and scope.get('groups')==3 and
                         case_bound==6 and graph_bound==12 and
                         scope.get('formats')==['Q2_K','IQ2_XXS'])
        need(record(effective['profile']['path'])==effective['profile'] and effective['kind']=='Q2-IQ2-fixture' and
             profile['unloaded_GPU_fixture'] and terminal['kind']=='Q2-IQ2-fixture' and terminal['model_loads']==0 and
             component['completed'] and component['model_loads']==0 and component['all_backends_positively_retired'] and
             component['source_descriptor_and_scratch_retired'] and case_bound in (6,12) and
             (graph_bound==12*case_bound or arithmetic_only) and
             1<=len(component['cases'])<=case_bound and 0<=component['GPU_graphs']<=graph_bound and type(component['all_outputs_reference_valid']) is bool and
             all(r['backends_positively_retired'] for r in component['cases']) and completed['unloaded_IQ2_fixture'],
             'Positive finite unloaded IQ2 owner retirement required; a numerical negative may close normally')
        need(load(observer/'native.IQ2-component.private.json')==component,'The two native component reports differ')
    need(completed['completed'] and completed['POSTs']==(0 if finite else 3) and completed['automatic_retries']==0 and
         completed['model_source_GPU_owners_positively_retired'] and completed['native_binding']==first,
         'Complete once-only normal API, frame and resource evidence required')
    need(terminal['completed'] and terminal['pid']==first['pid'] and terminal['run_id']==case['run_id'] and
         terminal['candidate_SELF_sha256']==case['SELF']['sha256'] and terminal['model_receipt_sha256']==first['model_receipt_sha256'] and
         terminal['HTTP_requests']==(0 if finite else 2) and terminal['VideoOut_starts']==(0 if finite else 1) and
         (finite or terminal['passive_monitor_and_API_completed']) and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         (finite or terminal['full_F32_continuation_and_routes_passed']) and terminal['source_windows']==terminal['source_completed_windows'],
         'Exact native owner and positive completed model/source/device retirement required')
    rows=terminal['requests']
    need(len(rows)==count and all(r['request_reset_completed'] and r['full_F32_finite'] and type(r['counting_quality_passed']) is bool for r in rows),
         'All three original finite requests must positively complete')
    need(launch['completed'] and launch['operation_calls']==1 and launch['app_id']>0,'One accepted ordinary native launch required')
    args.out.mkdir(parents=True,exist_ok=False)
    remote=PHYSICAL+case['report'][5:]
    arm=count-1 if finite and not args.IQ2_fixture else 2
    reports=[dict(record(terminal_path),remote=remote)]
    if unloaded_CPU:
        reports.append(dict(record(observer/'native.audit.private.json'),remote=remote+'.audit'))
    elif args.IQ2_fixture:
        reports.append(dict(record(observer/'native.IQ2-component.private.json'),remote=remote+'.IQ2-component'))
    else:reports.append(dict(record(observer/('native.arm'+str(arm)+'.result.private.bin')),remote=remote+'.arm'+str(arm)+'.result'))
    if args.headless_calibration or (args.headless_audit and not unloaded_CPU):
        route_path=observer/('native.arm'+str(arm)+'.routes.private.json');routes=load(route_path)
        need(routes['complete'] and not routes['capture_failed'] and routes['sidecar_written_after_model_and_source_retirement'] and
             routes['pid']==first['pid'] and routes['run_id']==case['run_id'],'Complete original headless route evidence required')
        reports.append(dict(record(route_path),remote=remote+'.arm'+str(arm)+'.routes'))
    close=dict(completed=True,all_model_source_device_owners_positively_retired=True,device_ledger_live_bytes=0,
        pid=first['pid'],app_id=launch['app_id'],reports=reports)
    CPU_startup=False
    if args.headless_audit and profile['headless_audit_kind']=='CPU-startup-staging-memory':
        from price_cpu_startup_original_reader import require_CPU_profile
        require_CPU_profile(Path(case['package']['path']))
        self_read=terminal['audit']['main_SELF']
        need(unloaded_CPU and count==0 and not terminal['audit']['model_sources_initialized'] and
             terminal['audit']['source_workers_created']==terminal['audit']['source_payload_reads']==0 and
             self_read['completed'] and self_read['full_current_SELF_SHA256_passed'] and
             self_read['SELF_sha256']==case['SELF']['sha256'] and self_read['SELF_bytes']==case['SELF']['bytes'] and
             self_read['minimum_sampled_free']>=self_read['selected_CPU_floor']==919,
             'Exact positive original-reader CPU startup completion required')
        CPU_startup=True
        close['source_bound_CPU_startup_profile']=package['effective_application_policy']['profile']
    state_path=args.current/'active-console.private.json';state=load(state_path)
    need(state['active_successful_native_case']['run_id']==case['run_id'] and state['native_running'], 'Exact active native case required')
    state.update(model_loaded=False,unknown_completion=False,state='current_model_positively_retired_ordinary_close_pending')
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    lan=lan_module();boot=load(case['model_proof']['path'])['current_boot']
    journal=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(first['pid'])+'.stages'
    deadline=time.monotonic()+5
    while True:
        stages=lan.web('/fs'+urllib.parse.quote(journal,safe='/'),8<<20)
        if completed_terminal_journal(stages,CPU_startup):break
        need(time.monotonic()<deadline,'Complete native terminal journal is pending; retain owner');time.sleep(.1)
    stage_path=args.out/'completed-native-stages.private.log';stage_path.write_bytes(stages)
    reports.append(dict(record(stage_path),remote=journal))
    prior_refusal=None
    if args.prior_refused_close:
        need(args.headless_audit and arm==2,'Only the corrected third-arm headless proof is admitted')
        prior=load(args.prior_refused_close/'result.private.json')
        prior_plan=load(args.prior_refused_close/'plan.private.json')
        previous=prior_plan['close_admission']
        corrected=[dict(row) for row in previous['reports']]
        need(len(corrected)==4 and corrected[2]['remote']==remote+'.arm0.routes',
             'The refused helper must contain the known headless route-path defect')
        corrected[2]['remote']=remote+'.arm2.routes'
        need(record(corrected[3]['path'])=={k:v for k,v in corrected[3].items() if k!='remote'},
             'The original completed journal copy must remain byte-exact')
        corrected[3]['path']=reports[3]['path']
        need(prior['completed'] is False and prior['operation']=='close' and prior['operation_calls']==0 and
             prior['app_id']==-1 and prior['helper_exited'] and prior['helper_files_removed'] and
             record(prior['raw']['path'])==prior['raw'] and
             prior_plan['old_files']==prior_plan['new_files']==case['new_files'] and
             previous['pid']==first['pid'] and previous['app_id']==launch['app_id'] and corrected==reports,
             'Exact returned zero-close refusal and otherwise unchanged completed proof required')
        prior_refusal=dict(result=record(args.prior_refused_close/'result.private.json'),
            plan=record(args.prior_refused_close/'plan.private.json'),changed_scope='Correct third-arm route path',
            previous_OS_close_calls=0,model_relaunches=0)
    plan=build(args.workspace,args.mount_plan,case['new_files'],case['new_files'],[],'close',args.out/'ordinary-close',close=close)
    execute(lan,plan,args.out/'ordinary-close')
    deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
            owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
        if not owners:break
        need(time.monotonic()<deadline,'Ordinary close retirement unknown; never retry it');time.sleep(.25)
    old=current_files(args.current);need(old==case['old_files'],'Selected original files changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id']
    pending=[dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json'))
             for i,row in enumerate(old[:3])]
    restoration=build(args.workspace,args.mount_plan,case['new_files'],old,pending,'publish',args.out/'restore')
    direct=dict(workspace=args.workspace,mount_plan=args.mount_plan,qualified=args.direct_staging_proof) if args.direct_staging_proof else None
    publish(lan,pending,restoration,args.out/'restore',direct_staging=direct)
    state.update(state='unloaded_GPU_fixture_completed_ordinarily_closed_current_restored' if args.IQ2_fixture else 'current_model_completed_ordinarily_closed_original_restored',
        native_running=False,model_loaded=False,gateway_running=False,native_owners=0,unknown_completion=False,original_restored=True)
    state.pop('temporary_installed_SELF',None)
    state['active_successful_native_case'].update(phase='model-complete-ordinary-close-original-restored',native_pid=first['pid'])
    if not args.IQ2_fixture and not unloaded_CPU:
        state.update(current_boot_Qwen_model_admitted=True,current_boot_readmission_pending=False)
        state['successful_route_20261102']['native_model_admission_complete']=True
        state['successful_route_20261102']['current_boot_model_proof']=dict(native_terminal=record(terminal_path),
            observer=record(observer/'complete.private.json'),case=record(args.case_plan),SELF=case['SELF'])
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=dict(completed=True,native_model_requests=count,external_API_requests=0 if finite else 2,positive_native_frames=0 if finite else 2,
        all_model_source_device_owners_positively_retired=True,device_ledger_live_bytes=0,
        ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
        native_owners=0,unknown_completion=False,initializer_requests=0,automatic_retries=0,
        native_terminal=record(terminal_path),observer=record(observer/'complete.private.json'),
        all_counting_quality_passed=None if args.IQ2_fixture else all(r['counting_quality_passed'] for r in rows),
        optimization_benefit_qualified=False,production_adopted=False)
    if prior_refusal:result['corrected_headless_proof_after_zero_operation_refusal']=prior_refusal
    save(args.out/'result.private.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('native_terminal','observer')}))


if __name__=='__main__':main()
