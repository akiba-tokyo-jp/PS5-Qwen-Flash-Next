#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Close the exact returned P1 request guard after all initialization epochs completed."""
import argparse
import json
import re
from pathlib import Path
import time
import urllib.parse

from build_performance_quantizer import record
from run_native_paired_down import completed_operation
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import PHYSICAL,build,current_files,lan_module
from audit_expert_all_q2_safety import body

ENTRY='08c68e6997fc0ae231b79649496ae89970ccfa54fb7e9417dbe22f90edcfb63d'
SELF='dcad1baacefbe1a4f39402b1a24cf95335770a85592da83df28ca8074ad60f1e'
CHECKPOINT_ENTRY='411515f3af833fde580b3aa8a418d47efbcc2634f76358474582bcb458df3f78'
CHECKPOINT_SELF='7c2433678ba088085d9c627ab2112cbebc928a9a54ca1da1bac38d7081c4e26d'
G1_ENTRY='57a0dc13258bc4550e8f8f1d276fe02765e83c6be02ca2c05c916b8e46c20301'
G1_SELF='fc74cb5865e9caf7d061f0f5f5190124e65d541a2f32ac216566c3c6cdb742fc'
S1_ENTRY='ad4bedee1fa68fde8c5ac932813aad403401bbd15508becde377b8e649624112'
S1_SELF='e5284dfcaaca41562c2bf9e9003240d3a0fc566bb4cf4b80c516521758147163'


def audit(stages,failure):
    active=False;completed=0
    for line in stages.splitlines():
        if line==b'native_driver_single_producer_entered':need(not active,'Overlapping GPU epoch');active=True
        if line==b'native_driver_producer_completed_resources_owned':need(active,'Unmatched GPU completion');active=False;completed+=1
    need(not active and completed==5,'Exactly five completed initialization epochs required')
    need(stages.splitlines()[-2:]==[b'P1_before_request_phase ordinal=0 cold_output_crop=1',b'resident_additional_exception_work_stopped'],
         'Only the returned guard before the first request is admitted')
    need(not any(x in stages for x in (b'first_generation_intent_persisted',b'inference_before_tokenization',b'first_generation_before_bounded_prefill',b'fatal_operation=')),
         'No request work or fatal operation is admitted')
    need(failure['message']=='The bounded first-generation request and durable observers are required' and
         failure['native_resources_started'] is True and failure['model_loaded'] is True and failure['CPU_worker_completion_unknown'] is False,
         'Exact returned request guard required')
    upload=failure['resident_GPU_upload']
    need(upload['completed_copy_calls']==1307 and upload['completed_copy_bytes']==3549514400 and upload['original_fence_wait_reset_and_cleanup'],
         'All selected synchronous model uploads must have returned')


def audit_checkpoint(stages,failure,rows):
    active=False;completed=0;last_checkpoint=False
    for line in stages.splitlines():
        if line==b'native_driver_single_producer_entered':need(not active,'Overlapping GPU epoch');active=True;last_checkpoint=False
        if line==b'native_driver_producer_completed_resources_owned':need(active,'Unmatched completion');active=False;completed+=1
        if line==b'native_driver_checkpoint_completed_producer_retained':need(active,'Checkpoint without producer');last_checkpoint=True
    need(active and completed==15 and last_checkpoint,'Exact last active epoch must have a positive checkpoint')
    lines=stages.splitlines();need(lines[-3]==b'native_driver_checkpoint_completed_producer_retained' and
         lines[-2].startswith(b'native_Direct_budget_observation ') and lines[-1]==b'resident_additional_exception_work_stopped',
         'No GPU operation may follow the positive checkpoint and CPU admission')
    need(failure['message']=='Complete checkpoint cannot retain original reserves: ledger_live=6169821184 limit=6199160832 growth=121634816 Direct_available=2287992832 Direct_reserve=536870912 Flexible_available=440401920 Flexible_reserve=268435456' and
         failure['CPU_worker_completion_unknown'] is False and failure['native_resources_started'] is True and failure['model_loaded'] is True,
         'Only the exact returned preallocation quota predicate is admitted')
    need(len(rows)==2 and [r['ordinal'] for r in rows]==[0,1] and all(r['request_reset_completed'] and r['full_F32_finite'] and
         r['metrics']['generated_tokens']==1 for r in rows),'Exactly two completed one-row diagnostic requests required')


def audit_G1(stages,failure):
    active=False;completed=0
    for line in stages.splitlines():
        if line==b'native_driver_single_producer_entered':need(not active,'Overlapping GPU epoch');active=True
        if line==b'native_driver_producer_completed_resources_owned':need(active,'Unmatched completion');active=False;completed+=1
    lines=stages.splitlines()
    need(active and completed==2 and lines[-3]==b'native_driver_single_producer_entered' and
         lines[-2].startswith(b'native_Direct_budget_observation ') and lines[-1]==b'resident_additional_exception_work_stopped',
         'Only CPU graph construction after two completed model-upload epochs is admitted')
    need(failure['message']=='Context admission stopped; close the application normally' and
         failure['last_model_load_error']=='llama_init_from_model: failed to initialize the context: A real GPU backend is required; no CPU fused-sort fallback\n' and
         failure['CPU_worker_completion_unknown'] is False and failure['native_resources_started'] is True and failure['model_loaded'] is True and
         b'first_generation_intent_persisted' not in stages and b'F32_row ' not in stages,
         'The exact device-selection guard must refuse before target inference')
    upload=failure['resident_GPU_upload'];need(upload['completed_copy_calls']==1307 and upload['completed_copy_bytes']==3549514400 and
        upload['original_fence_wait_reset_and_cleanup'],'All selected synchronous model uploads must be complete')


def audit_S1(stages,failure):
    active=False;completed=0
    for line in stages.splitlines():
        if line==b'native_driver_single_producer_entered':need(not active,'Overlapping GPU epoch');active=True
        if line==b'native_driver_producer_completed_resources_owned':need(active,'Unmatched completion');active=False;completed+=1
    need(not active and completed==49 and stages.splitlines()[-4:]==[b'S1_online_auxiliary_retirement_completed',
        b'first_generation_request_reset_completed',b'F32_request_completed request=1 rows=23 failures=0',b'resident_additional_exception_work_stopped'],
        'All49 target/auxiliary epochs and final request reset must positively complete')
    rows=re.findall(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})',stages)
    need(len(rows)==23 and [int(r[1]) for r in rows]==list(range(1,24)) and all(r[0]==b'1' and r[2]==b'248320' for r in rows),
         'All23 completed first-request full-vocabulary rows required')
    need(failure['message']=='Only a positively reset complete captured request may certify backing' and
         failure['CPU_worker_completion_unknown'] is False and failure['native_resources_started'] is True and failure['model_loaded'] is True and
         failure['four_next']['complete_captures_elided']==6 and failure['four_next']['all_memory_rollbacks']==1,
         'Only the known CPU certificate mismatch after actual compact rollback is admitted')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','entry-receipt','direct-staging-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--checkpoint-preallocation-refusal',action='store_true')
    p.add_argument('--G1-integrated-device-refusal',action='store_true')
    p.add_argument('--S1-post-request-certificate-refusal',action='store_true')
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    expected_entry=CHECKPOINT_ENTRY if a.checkpoint_preallocation_refusal else ENTRY
    expected_SELF=CHECKPOINT_SELF if a.checkpoint_preallocation_refusal else SELF
    need(sum((a.checkpoint_preallocation_refusal,a.G1_integrated_device_refusal,a.S1_post_request_certificate_refusal))<=1,'One exact known CPU failure required')
    if a.G1_integrated_device_refusal:expected_entry,expected_SELF=G1_ENTRY,G1_SELF
    if a.S1_post_request_certificate_refusal:expected_entry,expected_SELF=S1_ENTRY,S1_SELF
    case=load(a.case_plan);entry=load(a.entry_receipt);first=load(a.case_plan.parent/'native-first-start.private.json')
    package=load(case['package']['path']);link=load(package['relink']['path']);launch=load(a.case_plan.parent/'launch/result.private.json')
    need(case['SELF']['sha256']==expected_SELF and first['candidate_SELF_sha256']==expected_SELF and first['run_id']==case['run_id'] and
         launch['completed'] and launch['operation_calls']==1,'Exact consumed P1 process required')
    for row in (case['SELF'],case['package'],package['relink'],entry['source'],entry['entry']):need(record(row['path'])==row,'Consumed source or image changed')
    need(entry['source']['sha256']==expected_entry and link['link_command'].count(entry['entry']['path'])==1,'Exact compiled entry must be linked')
    text=Path(entry['source']['path']).read_text(encoding='utf-8')
    if not(a.G1_integrated_device_refusal or a.S1_post_request_certificate_refusal):
        need('demo_prompt),256,1};' in text and 'const auto &result=trial.run(request,' in text,'The one-token request must reach the original guard')
    header=a.workspace/'llm-work/PS5-Qwen-Flash-Next/native/app/first_generation.h';contract=header.read_text(encoding='utf-8')
    if a.S1_post_request_certificate_refusal:
        need('completed_backing.complete(model,context,ordinal,result.request_reset_completed,checkpoints.captures,last_payload,checkpoints.maximum_payload_bytes);' in text and
             text.index('online_MTP_requests.push_back(shadow.report());')<text.index('completed_backing.complete(') and
             text.index('require_model_CPU_budget();require_unchanged_model();',text.index('const auto checkpoints=engine->checkpoint_validation_stats();'))<text.index('completed_backing.complete('),
             'The CPU certificate must follow positive MTP report, request reset, routes and existing physical guards')
    elif a.G1_integrated_device_refusal:
        profile=load(package['effective_application_policy']['profile']['path'])
        provider=load(profile['G1_fused_provider']['path'])
        need(record(profile['G1_fused_provider']['path'])==profile['G1_fused_provider'] and
             provider['graph'] in link['new_inputs'] and record(provider['graph_header']['path'])==provider['graph_header'] and
             provider['graph_header']['sha256']=='4cd1d90c1150e1cb354247c70df5c4e9667383a9c8a70dadbb188ea3b9b7d7b8',
             'Exact compiled CPU graph helper required')
        graph_header=Path(provider['graph_header']['path']).read_text(encoding='utf-8')
        need('==GGML_BACKEND_DEVICE_TYPE_GPU' in graph_header and 'GGML_BACKEND_DEVICE_TYPE_IGPU' not in graph_header and
             graph_header.index('if(!owned->backend)throw')<graph_header.index('owned->storage=ggml_new_tensor_3d'),
             'The guard must precede the coefficient arena and its GPU assignment')
    elif not a.checkpoint_preallocation_refusal:
        need('first_output_tokens = 32;' in contract and contract.index('request.max_output_tokens != first_output_tokens')<contract.index('intent(request);')<contract.index('engine_.tokenize('),
             'Exact bound refusal must precede persistence, tokenization and prefill')
    else:
        checkpoint=a.workspace/'llm-work/PS5-Qwen-Flash-Next/native/app/model_checkpoint.cpp'
        implementation=checkpoint.read_text(encoding='utf-8');capture=implementation[implementation.index('void ModelCheckpoint::capture('):]
        need(capture.index('admit(full-metadata);')<capture.index('llama_state_seq_get_data_ext('),
             'The CPU quota callback must run before the checkpoint state writer')
        admission=body(text,'admit_checkpoint') if 'void admit_checkpoint(' in text else text[text.index('        const auto admit_checkpoint='):text.index('        const auto external_metrics=')]
        need('growth=' in admission and 'throw std::runtime_error("Complete checkpoint cannot retain original reserves:' in admission and
             not any(x in admission for x in ('vkQueueSubmit','llama_process(','llama_state_seq_get_data_ext(')),
             'The exact quota lambda may not allocate/copy state or submit GPU work')
    lan=lan_module();state_path=a.current/'active-console.private.json';state=load(state_path);boot=state['current_boot']
    need(state['active_successful_native_case']['run_id']==case['run_id'],'Only the same existing owner may close')
    base=PHYSICAL+case['report'][5:];remote=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(first['pid'])+'.stages'
    failure_raw=lan.web('/fs'+urllib.parse.quote(base+'.failure',safe='/'),1<<20);stages=lan.web('/fs'+urllib.parse.quote(remote,safe='/'),8<<20)
    need(failure_raw==(a.case_plan.parent/'native.failure.private.json').read_bytes(),'The parked failure changed')
    completed_rows=[]
    if a.S1_post_request_certificate_refusal:audit_S1(stages,json.loads(failure_raw))
    elif a.G1_integrated_device_refusal:audit_G1(stages,json.loads(failure_raw))
    elif a.checkpoint_preallocation_refusal:
        completed_rows=[load(a.case_plan.parent/('completed-first-rows/arm'+str(i)+'.private.json')) for i in (0,1)]
        audit_checkpoint(stages,json.loads(failure_raw),completed_rows)
    else:audit(stages,json.loads(failure_raw))
    time.sleep(.25);need(lan.web('/fs'+urllib.parse.quote(remote,safe='/'),8<<20)==stages,'The completed journal must be parked')
    a.out.mkdir(parents=True,exist_ok=False);reports=[]
    for name,raw,target in [('failure',failure_raw,base+'.failure'),('stages',stages,remote)]:
        path=a.out/(name+'.private.log');path.write_bytes(raw);reports.append(dict(record(path),remote=target))
    if a.S1_post_request_certificate_refusal:
        remote_ledger=base+'.arm0.token-ledger';raw=lan.web('/fs'+urllib.parse.quote(remote_ledger,safe='/'),1<<20)
        tokens=[json.loads(line) for line in raw.splitlines()];need(len(tokens)==22 and [r['generated_tokens'] for r in tokens]==list(range(1,23)),
            'All22 durably closed native token records required')
        path=a.out/'token-ledger.private.log';path.write_bytes(raw);reports.append(dict(record(path),remote=remote_ledger))
    proof=dict(known_P1_pre_request_contract_failure=True,model_loaded=True,all_GPU_epochs_positively_completed=5,
        target_request_operations=0,all_source_IO_completed=True,CPU_worker_completion_unknown=False,
        source_audit_SHA256=ENTRY,SELF_SHA256=SELF,pid=first['pid'],app_id=launch['app_id'],reports=reports)
    if a.checkpoint_preallocation_refusal:
        proof=dict(known_P1_checkpoint_preallocation_refusal=True,model_loaded=True,completed_requests=2,completed_GPU_epochs=15,
            last_active_epoch_positive_checkpoint=True,post_checkpoint_GPU_submissions=0,all_source_IO_completed=True,
            CPU_worker_completion_unknown=False,source_audit_SHA256=expected_entry,SELF_SHA256=expected_SELF,
            pid=first['pid'],app_id=launch['app_id'],reports=reports)
    if a.G1_integrated_device_refusal:
        proof=dict(known_G1_IGPU_graph_contract_failure=True,model_loaded=True,completed_GPU_epochs=2,last_active_epoch_CPU_graph_only=True,
            target_request_operations=0,all_source_IO_completed=True,CPU_worker_completion_unknown=False,
            source_audit_SHA256=expected_entry,SELF_SHA256=expected_SELF,pid=first['pid'],app_id=launch['app_id'],reports=reports)
    if a.S1_post_request_certificate_refusal:
        proof=dict(known_S1_post_request_backing_certificate_failure=True,model_loaded=True,completed_GPU_epochs=49,completed_F32_rows=23,
            completed_token_records=22,auxiliary_positively_retired=True,all_source_IO_completed=True,CPU_worker_completion_unknown=False,
            source_audit_SHA256=expected_entry,SELF_SHA256=expected_SELF,pid=first['pid'],app_id=launch['app_id'],reports=reports)
    save(a.out/'source-audit.private.json',dict(completed=True,entry=entry['source'],contract=record(header),proof=proof,
        model_and_device_backing_retained_until_ordinary_OS_exit=True,preclose_zero_device_ledger_claimed=False))
    plan=build(a.workspace,a.mount_plan,case['new_files'],case['new_files'],[],'close',a.out/'ordinary-close',close=proof)
    if not a.execute:return
    result=completed_operation(lan,plan,a.out/'ordinary-close');need(result['operation_calls']==1,'Exactly one ordinary close required')
    deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
        if not owners:break
        need(time.monotonic()<deadline,'Ordinary exit unknown; no repeated close');time.sleep(.25)
    old=current_files(a.current);need(old==case['old_files'],'Selected production inputs changed');prefix='/data/ai/moss-qwen-case-'+case['run_id']
    pending=[dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')) for i,row in enumerate(old[:3])]
    restore=build(a.workspace,a.mount_plan,case['new_files'],old,pending,'publish',a.out/'restore')
    publish(lan,pending,restore,a.out/'restore',direct_staging=dict(workspace=a.workspace,mount_plan=a.mount_plan,qualified=a.direct_staging_proof))
    save(a.out/'result.private.json',dict(completed=True,ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
        all_five_initialization_GPU_epochs_completed=not(a.checkpoint_preallocation_refusal or a.G1_integrated_device_refusal or a.S1_post_request_certificate_refusal),
        target_request_operations=2 if a.checkpoint_preallocation_refusal else 1 if a.S1_post_request_certificate_refusal else 0,
        checkpoint_preallocation_refusal=a.checkpoint_preallocation_refusal,
        G1_integrated_device_refusal=a.G1_integrated_device_refusal,
        S1_post_request_certificate_refusal=a.S1_post_request_certificate_refusal,
        last_active_epoch_positive_checkpoint=a.checkpoint_preallocation_refusal,native_owners=0,unknown_completion=False,
        source_audit=record(a.out/'source-audit.private.json'),GPU_capacity_readmission_pending=True,initializer_requests=0,automatic_retries=0))
    state.update(state='P1_pre_request_contract_failure_ordinarily_closed_current_restored',original_restored=True,native_running=False,
        model_loaded=False,native_owners=0,unknown_completion=False,GPU_retirement_readmission_pending=True,
        GPU_retirement_readmission_proof=record(a.out/'result.private.json'))
    state.pop('temporary_installed_SELF',None);state['active_successful_native_case']['phase']='P1-pre-request-refusal-ordinary-close-current-restored'
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=True,ordinary_close=1,current_restored=True,
        target_request_operations=2 if a.checkpoint_preallocation_refusal else 1 if a.S1_post_request_certificate_refusal else 0)))


if __name__=='__main__':main()
