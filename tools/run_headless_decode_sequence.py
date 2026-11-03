#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one headless ABBA, retaining completed cases if a later scope cannot start."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from build_performance_quantizer import record
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def returned(root,package):
    result=load(root/'result.private.json');plan=load(root/'case/plan.private.json')
    need(result['completed'] and plan['package']==record(package),'Exact completed package required')
    for name in ('terminal','closure'):need(record(result[name]['path'])==result[name],'Completed evidence changed')
    terminal=load(result['terminal']['path']);closed=load(result['closure']['path'])
    need(terminal['completed'] and terminal['timings_usable_for_performance'] and len(terminal['requests'])==3 and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and not closed['unknown_completion'],
         'All three timed requests and positive ordinary restoration required')
    need(all(r['counting_quality_passed'] and r['full_F32_finite'] and r['request_reset_completed'] for r in terminal['requests']),
         'Every counting, finite and state-reset decision must pass before advancing')
    need(b'F32_row request=' not in (root/'case/native-stages.private.log').read_bytes(),
         'Qualification-only full-vocabulary SHA must be absent from timing')
    return dict(root=str(root.resolve()),package=record(package),result=record(root/'result.private.json'),
                terminal=result['terminal'],closure=result['closure'],plan=record(root/'case/plan.private.json'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','model-proof','direct-staging-proof','control','candidate','numerical-proof','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--control-price',type=Path);p.add_argument('--candidate-price',type=Path)
    p.add_argument('--native-VM-proof',type=Path)
    p.add_argument('--default-readiness-pages',type=int,default=7374)
    p.add_argument('--scope',choices=('S1','P1','G1'),required=True);p.add_argument('--case-base',type=int,required=True)
    p.add_argument('--completed-case',type=Path,action='append',default=[],help='Reuse only the already completed prefix of this exact ABBA')
    a=p.parse_args();proof=load(a.numerical_proof)
    need(proof['completed'],'A completed numerical decision is required')
    if a.scope=='S1':need(proof.get('actual_target_tokens_bytes_causal_inputs_routes_and_all69_F32_rows_exact') is True,'Actual compact MTP lifetime and causal qualification required')
    else:
        need(proof['tokens_and_output_bytes_exact'] and all(proof['ordered_routes_exact_per_request']), 'Actual target outputs and ordered routes must match')
        if a.scope=='G1':need(proof['whole_F32_bytes_routes_tokens_exact'],'Same-computation fused ranking requires all69 exact rows')
        else:need(proof['matching_F32_rows']==69 or (proof['matching_F32_rows']==68 and
            [(r['request'],r['row']) for r in proof['differing_rows']]==[(1,1)] and
            proof['first_row_maximum_absolute_error_against_original'] is not None), 'P1 differences must be completely bounded and disclosed')
    order=[a.control,a.candidate,a.candidate,a.control];prices=[a.control_price,a.candidate_price,a.candidate_price,a.control_price]
    need(len(a.completed_case)<4 and a.default_readiness_pages>=7374,'A finite remaining ABBA and unchanged default screen required')
    rows=[returned(root,order[i]) for i,root in enumerate(a.completed_case)]
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'intent.private.json',dict(scope=a.scope,order=[record(x) for x in order],numerical_proof=record(a.numerical_proof),
        reused_completed_cases=rows,automatic_retries=0,completed_native_work_must_not_be_replayed=True))
    for index in range(len(rows),4):
        package=order[index];root=a.out/f'case-{a.case_base+index}';profile=load(load(package)['effective_application_policy']['profile']['path'])
        price=prices[index];readiness=a.default_readiness_pages;flags=[]
        if price:
            pricing=load(price);readiness=pricing['selected_readiness_pages']
            option='--staged-MTP-startup-pricing' if profile['headless_audit_kind']=='S1-persistent-MTP-online' else '--ordinary-target-pricing'
            flags=[option,str(price)]
        command=[sys.executable,'-B',str(ROOT/'tools/run_successful_headless_audit.py')]
        for name in ('workspace','current','mount-plan','model-proof','direct-staging-proof'):
            command+=['--'+name,str(getattr(a,name.replace('-','_')))]
        command+=['--package',str(package),'--out',str(root),'--readiness-pages',str(readiness)]+flags
        if a.native_VM_proof:command+=['--native-VM-proof',str(a.native_VM_proof)]
        log=a.out/f'case-{a.case_base+index}.private.log'
        with log.open('xb') as stream:
            child=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT);notice=0
            while child.poll() is None:
                if time.monotonic()>=notice:print(json.dumps(dict(scope=a.scope,index=index,case=a.case_base+index,running=True)),flush=True);notice=time.monotonic()+30
                time.sleep(1)
        if child.returncode:
            save(a.out/'stopped.private.json',dict(completed=False,positive_completed_cases=rows,failed_index=index,
                failed_case=str(root),log=record(log),automatic_retries=0,remaining_cases_not_submitted=True))
            raise RuntimeError('Sequence stopped; retain completed cases and inspect '+str(log)+'; never replay a consumed operation')
        row=returned(root,package);rows.append(row);save(a.out/'progress.private.json',dict(scope=a.scope,positive_completed_cases=rows))
    save(a.out/'result.private.json',dict(completed=True,scope=a.scope,cases=rows,order=[0,1,1,0],
        numerical_proof=record(a.numerical_proof),all_ordinary_closes_and_exact_restores=True,automatic_retries=0,
        native_requests=12,performance_analysis_pending=True,production_adopted=False))
    print(dict(completed=True,scope=a.scope,requests=12,reused_completed_cases=len(a.completed_case)))


if __name__=='__main__':main()
