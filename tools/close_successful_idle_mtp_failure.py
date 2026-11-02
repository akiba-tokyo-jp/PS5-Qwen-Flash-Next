#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Close only the exact CPU prefill-contract failure after all five GPU epochs returned."""
import argparse
import json
from pathlib import Path
import re
import time
import urllib.parse

from build_performance_quantizer import record
from run_successful_model_case import publish
from start_success_route import load,need,save
from success_case_control import PHYSICAL,build,current_files,execute,lan_module

ENTRY='16e60fcc805ace70534fe4b2efeaa17b924d0535034d639123521fc8c9a03af9'
RUNTIME='a7cefb4bcd39d5de4fc60ca73b35cf6c5342d989bbc6243853cca969f94cdb81'
SELF='e16b5b2ebd3bf5882d0b1bc814e830070276f81b91ec41acaa1cc0e03eee12da'


def audit(stages):
    lines=stages.splitlines();active=False;completed=0
    for line in lines:
        if line==b'native_driver_single_producer_entered':need(not active,'Overlapping GPU epoch');active=True
        if line==b'native_driver_producer_completed_resources_owned':need(active,'Unmatched GPU completion');active=False;completed+=1
    need(not active and completed==5,'All five actual initialization epochs must have returned positively')
    need(lines[-8:]==[b'native_driver_single_producer_entered',b'native_driver_positive_device_idle_same_generation_reused',
        b'native_driver_producer_completed_resources_owned',b'first_generation_intent_persisted',b'inference_before_tokenization',
        b'inference_tokenization_completed',b'first_generation_before_bounded_prefill',b'resident_additional_exception_work_stopped'],
        'Only the exact returned CPU check before target prefill is admitted')
    constructor_label=b'native_driver_owner_ready owned_BO_bytes=0 constructor_allocations=unknown'
    need(not any(b'S1_shadow_' in line or b'fatal' in line or (b'unknown' in line and line!=constructor_label) for line in lines),
         'No auxiliary work, unknown completion or fatal is admitted')
    need(b'source_pipeline_CPU_preflight_passed_before_Vulkan GPU_not_started=1' in lines and
         b'model_load_completed' in lines,'Positive original source preflight and model upload required')
    budgets=re.findall(rb'native_Direct_budget_observation reported_total=(\d+) .*?free_first=(\d+) free_last=(\d+)',stages)
    need(budgets,'Observed pre-model Direct baseline required')
    return max(min(int(a),int(b)) for _,a,b in budgets)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','entry-receipt','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    case=load(a.case_plan);first=load(a.case_plan.parent/'native-first-start.private.json');entry=load(a.entry_receipt)
    launch=load(a.case_plan.parent/'launch/result.private.json');package=load(case['package']['path']);relink=load(package['relink']['path'])
    need(case['SELF']['sha256']==SELF and first['candidate_SELF_sha256']==SELF and first['run_id']==case['run_id'] and
         launch['completed'] and launch['operation_calls']==1,'Exact consumed S1 title required')
    for row in [case['package'],package['relink'],entry['source'],entry['entry'],entry['provider'],*entry['inputs']]:
        need(record(row['path'])==row,'The exact consumed source or object changed')
    need(entry['source']['sha256']==ENTRY and entry['inputs'][2]['sha256']==RUNTIME and
         all(relink['link_command'].count(entry[k]['path'])==1 for k in ('entry','provider')),'Only the exact audited complete prefill-check sources are admitted')
    runtime=Path(entry['inputs'][2]['path']).read_text(encoding='utf-8')
    need('need(n==s.prompt&&!s.prefilled,"One exact target prefill required");' in runtime and
         runtime.index('need(n==s.prompt&&!s.prefilled')<runtime.index('s.target.prefill(n);'),
         'The observed exception must precede the target prefill, hidden download and auxiliary initialization')
    if a.out.exists():need(a.execute and (a.out/'ordinary-close/plan.private.json').is_file(),'Only one prepared close may execute')
    else:a.out.mkdir(parents=True,exist_ok=False)
    lan=lan_module();base=PHYSICAL+case['report'][5:]
    boot=load(case['model_proof']['path'])['current_boot'];journal=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(first['pid'])+'.stages'
    raw=lan.web('/fs'+urllib.parse.quote(base+'.failure',safe='/'),1<<20)
    need(raw==(a.case_plan.parent/'native.failure.private.json').read_bytes(),'The parked failure changed')
    failure=json.loads(raw);need(failure['message']=='One exact target prefill required' and failure['model_loaded'] is True and
        failure['native_resources_started'] is True and failure['CPU_worker_completion_unknown'] is False and
        failure['resident_GPU_upload']['completed_copy_calls']==1444 and failure['resident_GPU_upload']['completed_copy_bytes']==4519798432 and
        failure['resident_GPU_upload']['original_fence_wait_reset_and_cleanup'],'Exact returned CPU-only contract failure after completed model upload required')
    stages=lan.web('/fs'+urllib.parse.quote(journal,safe='/'),8<<20);baseline=audit(stages);time.sleep(.25)
    need(lan.web('/fs'+urllib.parse.quote(journal,safe='/'),8<<20)==stages,'The owner must be parked after positive completion')
    reports=[]
    for name,data,remote in [('failure',raw,base+'.failure'),('stages',stages,journal)]:
        target=a.out/(name+'.private.log')
        if target.exists():need(target.read_bytes()==data,'A prepared completed proof changed')
        else:target.write_bytes(data)
        reports.append(dict(record(target),remote=remote))
    proof=dict(known_MTP_returned_prefill_scope_failure=True,model_loaded=True,all_GPU_epochs_positively_completed=5,
        target_prefill_GPU_calls=0,auxiliary_contexts_created=0,all_source_IO_completed=True,CPU_worker_completion_unknown=False,
        source_audit_SHA256=ENTRY,pid=first['pid'],app_id=launch['app_id'],reports=reports)
    source_audit=dict(completed=True,entry=entry['source'],runtime=entry['inputs'][2],proof=proof,
        preclose_model_and_device_owners_retained=True,preclose_zero_device_ledger_claimed=False,
        Direct_pre_model_available_baseline=baseline,automatic_retries=0,GPU_reset_calls=0)
    if (a.out/'source-audit.private.json').exists():need(load(a.out/'source-audit.private.json')==source_audit,'Prepared source audit changed')
    else:save(a.out/'source-audit.private.json',source_audit)
    if (a.out/'ordinary-close/plan.private.json').exists():
        plan=load(a.out/'ordinary-close/plan.private.json')
        need(plan['close_admission']==proof and all(record(plan[k]['path'])==plan[k] for k in ('artifact','controller','context','source')),
             'The exact prepared once-only ordinary close must remain unchanged')
    else:plan=build(a.workspace,a.mount_plan,case['new_files'],case['new_files'],[],'close',a.out/'ordinary-close',close=proof)
    if not a.execute:return
    execute(lan,plan,a.out/'ordinary-close');deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
        if not owners:break
        need(time.monotonic()<deadline,'Ordinary OS exit unknown; never retry it');time.sleep(.25)
    old=current_files(a.current);need(old==case['old_files'],'Selected current deployment changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id']
    pending=[dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')) for i,row in enumerate(old[:3])]
    restore=build(a.workspace,a.mount_plan,case['new_files'],old,pending,'publish',a.out/'restore');publish(lan,pending,restore,a.out/'restore')
    direct=build(a.workspace,a.mount_plan,old,old,[],'observe-direct',a.out/'Direct-after-exit');execute(lan,direct,a.out/'Direct-after-exit')
    direct_log=(a.out/'Direct-after-exit/execution/console.private.log').read_bytes()
    match=re.search(rb'DIRECT_POOL total=(\d+) query_rc=0 largest_start=(\d+) largest_available=(\d+) query_only=1',direct_log)
    need(match,'A positive post-exit Direct query is required');available=int(match[3]);returned=available>=baseline
    state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['active_successful_native_case']['run_id']==case['run_id'],'Exact active S1 scope required')
    state.update(state='S1_known_CPU_prefill_failure_ordinarily_closed_current_restored',native_running=False,model_loaded=False,
        native_owners=0,gateway_running=False,unknown_completion=not returned,original_restored=True,current_boot_readmission_pending=True,
        current_boot_Qwen_model_admitted=False,ordinary_OS_Direct_return_observed=returned)
    state.pop('temporary_installed_SELF',None);state['active_successful_native_case']['phase']='known-CPU-prefill-failure-closed-current-restored'
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    result=dict(completed=returned,ordinary_OS_closes=1,ordinary_exit_observed=True,current_seven_restored_and_native_hashed=True,
        Direct_pre_model_available_baseline=baseline,post_exit_largest_Direct_available=available,
        Direct_return_at_least_pre_model_baseline=returned,native_owners=0,unknown_completion=not returned,
        preclose_zero_ledger_claimed=False,source_audit=record(a.out/'source-audit.private.json'),
        initializer_requests=0,GPU_reset_calls=0,automatic_retries=0,numerics_or_speed_qualified=False)
    save(a.out/'result.private.json',result);need(returned,'Post-exit Direct ownership readmission failed; no further launch')
    print(json.dumps(result))


if __name__=='__main__':main()
