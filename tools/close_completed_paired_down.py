#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Ordinarily close the exact standalone owner after its final positive boundary."""
import argparse
import json
from pathlib import Path
import time
import urllib.parse

from build_performance_quantizer import record
from run_native_paired_down import completed_operation
from run_successful_model_case import publish
from start_success_route import load, need, save
from success_case_control import PHYSICAL, build, current_files, lan_module

SOURCE='2d356cca75a0fb594e0c94fb8bdca17fd82d114b0cce7242ed300626942f1b8b'
SUPPORT='b193d0659c68bb569bbba22cf59b88d2691bcd49ab1d673f1e9a64b5328d6f7e'
SELF='51ea93720d80ce338a6be99f2c0697f3471b307cd5f5fa6fc3ebf6726ebf30d7'


def audit(result, stages):
    rows=result['cases']
    need(result['completed'] is False and len(rows)==24 and result['positive_reference_dispatches']==24,
         'Exactly 24 completed numerical cases required')
    need(result['physical_GPU_execution'] and result['PS5_GPU_execution'] and not result.get('unknown_completion',False),
         'Every native fence must have returned positively')
    need(all(r['positive_fence'] and r['all_case_resources_retired'] and r['all_outputs_passed'] and
             r['canaries_exact'] and r['mismatches']==0 and r['Vulkan_dispatches']==1 for r in rows),
         'All numerical cases, resources and canaries must pass')
    lines=stages.splitlines()
    for marker in (b'native_driver_before_positive_device_idle',b'native_driver_device_idle_completed',
                   b'native_driver_before_completed_epoch_retirement'):
        need(lines.count(marker)==25,'All 25 positive driver boundary records required')
    need(lines.count(b'native_driver_checkpoint_completed_producer_retained')==24,
         'Every case must reach its positive completed checkpoint')
    need(lines.count(b'native_driver_producer_completed_resources_owned')==1,
         'Exactly one final frontend completion required')
    need(lines[-5:]==[b'native_driver_before_positive_device_idle',b'native_driver_device_idle_completed',
        b'native_driver_before_completed_epoch_retirement',b'native_driver_producer_completed_resources_owned',
        b'fatal_operation=paired_Down_native_unknown_GPU_scope_retained'],
        'Only the exact post-positive-completion CPU exception is admitted')
    need(sum(line.startswith(b'fatal_operation=') for line in lines)==1,
         'No earlier unknown scope is admitted')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','direct-staging-proof','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    case=load(a.case_plan);package=load(case['package']['path']);link=load(package['relink']['path'])
    need(record(case['package']['path'])==case['package'] and record(package['relink']['path'])==package['relink'] and
         case['SELF']['sha256']==SELF and record(case['SELF']['path'])==case['SELF'], 'Exact consumed native image required')
    need(record(link['source']['path'])==link['source'] and link['source']['sha256']==SOURCE,'Actual compiled source changed')
    support=next(r for r in link['inputs_before'] if Path(r['path']).name=='paired_down_native_support.h')
    need(record(support['path'])==support and support['sha256']==SUPPORT,'Actual compiled support changed')
    source=Path(link['source']['path']).read_text(encoding='utf-8')
    close='void close(){qwen_native_driver_complete();const auto epoch=native_completed_epoch();vkDestroyDevice(device,nullptr);device=VK_NULL_HANDLE;destroy_instance(instance,nullptr);instance=VK_NULL_HANDLE;native_component_finish(epoch);}'
    need(source.count(close)==1,'Only the exact final positive boundary and subsequent CPU teardown are admitted')
    tail=source[source.index('    a.vkDestroyPipelineLayout(a.device,layout,nullptr);'):]
    need(tail.index('a.close();')<tail.index('result["completed"]=true') and 'vkQueueSubmit' not in tail,
         'No queue work may follow final completion')
    a.out.mkdir(parents=True,exist_ok=False);lan=lan_module();state_path=a.current/'active-console.private.json';state=load(state_path)
    need(state['active_successful_native_case']['run_id']==case['run_id'],'The exact existing owner is required')
    remote=PHYSICAL+case['report'][5:]
    first_raw=lan.web('/fs'+urllib.parse.quote(remote+'.first.start',safe='/'),8192,8);first=json.loads(first_raw)
    need(first['run_id']==case['run_id'] and first['candidate_SELF_sha256']==SELF,'Exact existing process identity required')
    boot=state['current_boot'];stage_remote=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(first['pid'])+'.stages'
    result_raw=lan.web('/fs'+urllib.parse.quote(remote,safe='/'),1<<20,8)
    stages=lan.web('/fs'+urllib.parse.quote(stage_remote,safe='/'),8<<20,8);result=json.loads(result_raw);audit(result,stages)
    need(result['pid']==first['pid'] and result['run_id']==case['run_id'] and result['candidate_SELF_sha256']==SELF,
         'Completed cases must belong to the same native owner')
    time.sleep(.25)
    need(lan.web('/fs'+urllib.parse.quote(stage_remote,safe='/'),8<<20,8)==stages and
         lan.web('/fs'+urllib.parse.quote(remote,safe='/'),1<<20,8)==result_raw,'Parked completion records changed')
    reports=[]
    for name,data,path in [('first',first_raw,remote+'.first.start'),('cases',result_raw,remote),('stages',stages,stage_remote)]:
        target=a.out/(name+'.private.log');target.write_bytes(data);reports.append(dict(record(target),remote=path))
    launch=load(a.case_plan.parent/'launch/result.private.json')
    need(launch['completed'] and launch['operation_calls']==1,'One existing accepted launch required')
    proof=dict(known_paired_Down_post_completion_CPU_failure=True,model_loaded=False,positive_reference_dispatches=24,
        all_case_resources_retired=True,final_driver_producer_completed=True,all_source_IO_completed=True,
        CPU_worker_completion_unknown=False,source_audit_SHA256=SOURCE,support_SHA256=SUPPORT,
        pid=first['pid'],app_id=launch['app_id'],reports=reports)
    save(a.out/'source-audit.private.json',dict(completed=True,source=link['source'],support=support,proof=proof,
        zero_device_ledger_claimed=False,device_destruction_return_claimed=False,
        final_GPU_and_worker_completion_positive=True,CPU_Direct_table_backing_retained_until_ordinary_OS_exit=True,
        individual_BO_release_claimed=False,model_speed_qualified=False))
    close_plan=build(a.workspace,a.mount_plan,case['new_files'],case['new_files'],[],'close',a.out/'ordinary-close',close=proof)
    if not a.execute:return
    closed=completed_operation(lan,close_plan,a.out/'ordinary-close')
    need(closed['operation_calls']==1,'Exactly one ordinary OS close required')
    deadline=time.monotonic()+15
    while True:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        if not any(r['name']=='eboot.bin' for r in rows):break
        need(time.monotonic()<deadline,'Ordinary exit unknown; never repeat close');time.sleep(.25)
    old=current_files(a.current);need(old==case['old_files'],'Selected production inputs changed')
    prefix='/data/ai/moss-qwen-case-'+case['run_id']
    pending=[dict(row,target=row['remote'],remote=prefix+('-restore-SELF.bin' if i==0 else '-restore-'+str(i)+'.json')) for i,row in enumerate(old[:3])]
    restoration=build(a.workspace,a.mount_plan,case['new_files'],old,pending,'publish',a.out/'restore')
    publish(lan,pending,restoration,a.out/'restore',direct_staging=dict(workspace=a.workspace,mount_plan=a.mount_plan,qualified=a.direct_staging_proof))
    state.update(state='paired_Down_positive_GPU_completion_CPU_teardown_closed_current_restored',original_restored=True,
        native_running=False,model_loaded=False,gateway_running=False,native_owners=0,unknown_completion=False,
        GPU_retirement_readmission_pending=True)
    state.pop('temporary_installed_SELF',None)
    state['active_successful_native_case']['phase']='known-idle-CPU-teardown-ordinary-close-current-restored'
    state['paired_Down_positive_boundary_close']=record(a.out/'source-audit.private.json')
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    save(a.out/'result.private.json',dict(completed=True,ordinary_OS_closes=1,ordinary_exit_observed=True,
        current_seven_restored_and_native_hashed=True,positive_reference_dispatches=24,all_outputs_passed=True,
        source_audit=record(a.out/'source-audit.private.json'),native_owners=0,unknown_completion=False,
        GPU_capacity_readmission_pending=True,model_speed_qualified=False,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,ordinary_exit=True,exact_current_restored=True,positive_GPU_cases=24)),flush=True)


if __name__=='__main__':main()
