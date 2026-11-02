#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ordinarily close an explicit pre-GPU exception, then restore selected files."""
import argparse
import json
from pathlib import Path
import time
import urllib.parse

from build_performance_quantizer import record
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL


def returned_span_open_refusal(receipt,case,failure,stages):
    """Admit only the consumed pre-worker CPU exception, never a general override."""
    entry=load(receipt);package=load(case['package']['path']);relink=load(package['relink']['path'])
    bindings={
        '7696839d8f20e4ce17919420b4f907eb74d9e5cc8d97005f0b0f36872d99f53e':(
            'ca525151c6d1684cbfdd433d3f8f0b82bd9d36e187abfc84d4b404326a85977b',
            '6fa7218af50fdab6c725fbf8155a86ea86a2f0727c1eebf1830de2f9d2289e23',
            'Exact immutable Direct fixture source required',False),
        '807d852013a74a3c515675707b666b840ba11dde7e0826146abee75ddb00aa1f':(
            'fb5e11264c5d5e428a0980c94ef69ee2407d1737147e3a7be55e08dfcc82b890',
            '9af62facaac3dc691e659cb9563b2ece4e643b5ef21d964a5f677580182b5f08',
            'Same-launch whole-admitted SELF namespace required',True)}
    need(record(case['package']['path'])==case['package'] and record(package['relink']['path'])==package['relink'] and
         case['SELF']['sha256'] in bindings,
         'Only the exact consumed span-open program is admitted')
    expected_entry,expected_runtime,message,metadata_returned=bindings[case['SELF']['sha256']]
    for row in [entry['source'],entry['entry'],entry['provider'],*entry['inputs']]:
        need(record(row['path'])==row,'The complete compiled span-open input changed')
    need(entry['source']['sha256']==expected_entry and entry['inputs'][2]['sha256']==expected_runtime and
         all(relink['link_command'].count(entry[k]['path'])==1 for k in ('entry','provider')),
         'Exact complete pre-worker source and accepted link required')
    lines=stages.splitlines()
    tail=[b'resident_measured_GPU_phase_admitted_starting_GPU',b'I1_fixture_before_readonly_source_open']
    if metadata_returned:tail.append(b'I1_fixture_source_open_and_metadata_returned')
    tail.append(b'resident_additional_exception_work_stopped')
    need(failure['message']==message and failure['model_loaded'] is False and
         failure['native_resources_started'] is True and failure['CPU_worker_completion_unknown'] is True and
         lines[-len(tail):]==tail and
         b'source_pipeline_CPU_preflight_passed_before_Vulkan GPU_not_started=1' in lines and
         b'model_mapping_all_completed_ranges_unmapped mapped_files=76 unmapped_files=76 GPU_not_started=1 model_loaded=0' in lines,
         'Only the returned synchronous open/metadata failure before allocation and worker creation is admitted')
    text=Path(entry['source']['path']).read_text(encoding='utf-8')
    phase=text[text.index('        qwen_native_stage("resident_measured_GPU_phase_admitted_starting_GPU");'):]
    phase=phase[:phase.index('    }catch(const std::exception &e){')]
    need('qwen_native_gpu_initialize(' not in phase and 'llama_backend_init(' not in phase and
         'resident_worker_completion_unknown=true;' in phase and 'run_immutable_span_fixture' in phase,
         'The coarse unknown flag must precede the fixture, with no GPU initialization in this path')
    return dict(completed=True,compiled_entry=entry['source'],runtime=entry['inputs'][2],accepted_SELF=case['SELF'],
        original_source_preflight_returned=True,additional_worker_created=False,additional_scratch_allocated=False,
        GPU_initialized=False,model_loaded=False,all_CPU_IO_returned=True,
        coarse_unknown_flag_explained_by_exact_pre_worker_source=True,fixture_numerics_or_speed_qualified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--source-bound-span-open-refusal',type=Path)
    parser.add_argument('--early-S1-policy-refusal',type=Path,help='Exact consumed S1 build receipt for a returned legacy-policy mismatch')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    case=load(args.case_plan);start_path=args.case_plan.parent/'native-first-start.private.json'
    launch=load(args.case_plan.parent/'launch/result.private.json')
    need(launch['completed'] and launch['operation_calls']==1,'One accepted native launch required')
    lan=lan_module();base=PHYSICAL+case['report'][5:];early=not start_path.exists()
    if not early:
        start=load(start_path);pid=start['pid']
        need(start['run_id']==case['run_id'] and start['candidate_SELF_sha256']==case['SELF']['sha256'],
             'Exact positively observed native owner required')
    else:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
            owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
        need(len(owners)==1,'Exactly one accepted native owner required for early CPU refusal')
        pid=int(owners[0]['pid'])
        try:lan.absent(base+'.first.start')
        except Exception:raise ValueError('Early refusal already reached model-start scope; retain owner')
    prior=(args.case_plan.parent/'native.failure.private.json').read_bytes()
    failure_raw=lan.web('/fs'+urllib.parse.quote(base+'.failure',safe='/'),1<<20)
    need(prior==failure_raw,'The completed native failure changed')
    failure=json.loads(failure_raw)
    if not args.source_bound_span_open_refusal:
        need(failure['native_resources_started'] is False and failure['model_loaded'] is False and
             failure['CPU_worker_completion_unknown'] is False and failure['message'],'Known pre-GPU synchronous exception required')
    import re
    controller=Path(load(args.mount_plan)['controller']['path']).read_text()
    boot=re.search(r'boot.tv_sec!=(\d+)LL\|\|boot.tv_usec!=(\d+)LL',controller)
    remote=PHYSICAL+'/qwen-runtime/entry-b'+boot[1]+'-'+boot[2]+'-'+str(pid)+'.stages'
    stages=lan.web('/fs'+urllib.parse.quote(remote,safe='/'),8<<20)
    audited=None
    if args.source_bound_span_open_refusal:
        need(not early,'A source-bound accepted native owner is required')
        audited=returned_span_open_refusal(args.source_bound_span_open_refusal,case,failure,stages)
        time.sleep(.25)
        need(lan.web('/fs'+urllib.parse.quote(remote,safe='/'),8<<20)==stages,'The source-bound CPU journal must be parked')
        save(args.out/'source-audit.private.json',audited)
    if early:
        early_message=failure['message']=='Monitor clock calibration is stale or inconsistent'
        if args.early_S1_policy_refusal:
            package=load(case['package']['path']);effective=package['effective_application_policy'];profile=load(effective['profile']['path'])
            need(record(case['package']['path'])==case['package'] and record(effective['profile']['path'])==effective['profile'] and
                 effective['kind']=='headless-model-audit' and profile['headless_audit_kind']=='S1-MTP-shadow' and
                 profile['successful_MTP_contract_verified'] and failure['message']=='First-generation policy exceeds its exact admitted scope',
                 'Only the returned S1 legacy-policy mismatch before resource setup is admitted')
            entry=load(args.early_S1_policy_refusal)
            need(entry['application_policy']==effective['profile'] and record(entry['source']['path'])==entry['source'] and
                 record(entry['entry']['path'])==entry['entry'],'Exact consumed S1 entry required')
            CPU=next(row for row in entry['inputs'] if Path(row['path']).name=='model_cpu_budget.h')
            policy=load(args.case_plan.parent/'development.json')
            policy_binding=next(row for row in case['new_files'] if row['remote'].endswith('/qwen-runtime/development.json'))
            need(record(args.case_plan.parent/'development.json')=={k:policy_binding[k] for k in ('path','bytes','sha256')},
                 'The consumed native policy changed')
            need(record(CPU['path'])==CPU and 'model_CPU_budget_bytes = 672ull << 20;' in Path(CPU['path']).read_text(encoding='utf-8') and
                 policy['native_first_generation_validation']['CPU_budget_bytes']==512<<20,
                 'The old quota header must explain the exact legacy-policy mismatch')
            early_message=True
        need(early_message and
             b'CXX_initializers_completed' in stages and b'early_SELF_whole_Direct_hash_completed_at_main_entry_after_CXX' in stages and
             b'configuration_read GPU_not_started=1 model_loaded=0' in stages and
             b'resident_additional_exception_work_stopped' in stages and b'model_mapping_' not in stages and
             b'inference_before_' not in stages and b'native_GPU_initialize' not in stages,
             'Only the exact returned pre-model clock refusal with zero started probe ranges is admitted')
    else:
        need(b'model_mapping_all_completed_ranges_unmapped mapped_files=76 unmapped_files=76 GPU_not_started=1 model_loaded=0' in stages and
             b'resident_additional_exception_work_stopped' in stages,'Positive complete probe release and returned exception required')
    reports=[]
    for name,raw,path in (('failure',failure_raw,base+'.failure'),('stages',stages,remote)):
        target=args.out/(name+'.private.log');target.write_bytes(raw);reports.append(dict(record(target),remote=path))
    close=dict(known_returned_pre_GPU_exception=True,native_resources_started=False,model_loaded=False,
               CPU_worker_completion_unknown=False,all_probe_ranges_unmapped=True,pid=pid,app_id=launch['app_id'],reports=reports)
    close['probe_ranges_started']=0 if early else 76
    if audited:
        close=dict(CPU_only=True,all_CPU_IO_returned=True,pid=pid,app_id=launch['app_id'],reports=reports,
            source_bound_span_open_refusal=record(args.out/'source-audit.private.json'))
    plan=build(args.workspace,args.mount_plan,case['new_files'],case['new_files'],[],'close',args.out/'ordinary-close',close=close)
    execute(lan,plan,args.out/'ordinary-close')
    deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(r['name']=='eboot.bin' for r in rows):break
        need(time.monotonic()<deadline,'Ordinary close incomplete; no retry');time.sleep(.25)
    old=current_files(args.current);need(old==case['old_files'],'Selected originals changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id'];pending=[]
    for i,row in enumerate(old[:3]):
        pending.append(dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')))
    restoration=build(args.workspace,args.mount_plan,case['new_files'],old,pending,'publish',args.out/'restore')
    publish(lan,pending,restoration,args.out/'restore')
    path=args.current/'active-console.private.json';state=load(path)
    state.update(state='known_pre_GPU_model_exception_ordinarily_closed_current_restored',native_running=False,
                 model_loaded=False,gateway_running=False,native_owners=0,unknown_completion=False,original_restored=True,
                 current_boot_Qwen_model_admitted=False,current_boot_readmission_pending=True)
    state.pop('temporary_installed_SELF',None)
    state['active_successful_native_case'].update(phase='known-pre-GPU-exception-closed-original-restored',failure_message=failure['message'])
    path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=dict(completed=True,known_pre_GPU_exception=True,exception=failure['message'],GPU_initializations=0,
                model_probe_ranges_started=0 if early else 76,
                ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
                native_owners=0,initializer_requests=0,title_launches=0,automatic_retries=0)
    if audited:result['source_bound_span_open_refusal']=record(args.out/'source-audit.private.json')
    save(args.out/'result.private.json',result);print(json.dumps(result))


if __name__=='__main__':main()
