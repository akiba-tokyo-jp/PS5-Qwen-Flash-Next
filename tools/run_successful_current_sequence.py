#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run explicit finite packages sequentially, advancing only after ordinary restore."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import lan_module,PHYSICAL

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','model-proof','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--package',action='append',type=Path,required=True)
    parser.add_argument('--clock',type=Path,help='Historical receipt compatibility only; each case always creates a fresh calibration')
    parser.add_argument('--scope',choices=('P1','R1','R1-direct','G1-shadow','G1','F32'),required=True)
    parser.add_argument('--case-base',type=int,required=True)
    args=parser.parse_args();need(1<=len(args.package)<=4,'One explicit scope of at most four packages required')
    args.out.mkdir(parents=True,exist_ok=False)
    save(args.out/'intent.private.json',dict(packages=[record(p) for p in args.package],scope=args.scope,
        cases=list(range(args.case_base,args.case_base+len(args.package))),automatic_retries=0,
        advance_requires_positive_model_retirement_ordinary_close_and_exact_restore=True))
    def script(name,arguments,log):
        command=[sys.executable,'-B',str(ROOT/'tools'/name),*map(str,arguments)]
        with log.open('xb') as stream:
            child=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
            notice=0
            while child.poll() is None:
                if time.monotonic()>=notice:
                    print(json.dumps(dict(phase=name,case=current_case,host_child_running=True)),flush=True);notice=time.monotonic()+30
                time.sleep(1)
        need(child.returncode==0,'Scope stopped; inspect '+str(log)+'; never resubmit the consumed operation')
    common=['--workspace',args.workspace,'--current',args.current,'--mount-plan',args.mount_plan]
    records=[]
    for index,package in enumerate(args.package):
        current_case=args.case_base+index;case=args.out/('case-'+str(current_case));closed=args.out/('closed-'+str(current_case))
        clock=args.out/('clock-'+str(current_case))
        script('refresh_successful_clock.py',common+['--out',clock,'--execute'],args.out/('clock-'+str(current_case)+'.private.log'))
        script('run_successful_model_case.py',common+['--model-proof',args.model_proof,'--clock',clock/'clock.private.json',
            '--package',package,'--out',case,'--execute'],args.out/('start-'+str(current_case)+'.private.log'))
        deadline=time.monotonic()+1800;poll=0
        while True:
            script('observe_successful_model_start.py',['--case-plan',case/'plan.private.json'],
                args.out/('read-'+str(current_case)+'-'+str(poll)+'.private.log'));poll+=1
            if (case/'native.failure.private.json').exists():
                failure=load(case/'native.failure.private.json')
                if failure.get('native_resources_started') is False and failure.get('model_loaded') is False and failure.get('CPU_worker_completion_unknown') is False:
                    script('close_successful_model_failure.py',common+['--case-plan',case/'plan.private.json','--out',closed],
                           args.out/('refusal-close-'+str(current_case)+'.private.log'))
                raise RuntimeError('Known native refusal captured; sequence stopped without retry')
            need(not(case/'native.fatal.private.json').exists(),'Native fatal evidence; retain owner without retry')
            if (case/'native.demo.ready.private.json').exists():break
            need(time.monotonic()<deadline,'Ready deadline expired; retain owner without replay');time.sleep(3)
        script('observe_successful_current_normal.py',['--current',args.current,'--case-plan',case/'plan.private.json',
            '--out',case/'passive-observer'],args.out/('requests-'+str(current_case)+'.private.log'))
        # Refresh the same boot-qualified journal after native retirement and
        # collect the actual ordered routes and durable token payloads.
        script('observe_successful_model_start.py',['--case-plan',case/'plan.private.json'],args.out/('terminal-'+str(current_case)+'.private.log'))
        plan=load(case/'plan.private.json');lan=lan_module();remote=PHYSICAL+plan['report'][5:]
        for ordinal in range(3):
            for suffix,limit in (('routes',4<<20),('token-ledger',128<<10)):
                raw=lan.web('/fs'+urllib.parse.quote(remote+'.arm'+str(ordinal)+'.'+suffix,safe='/'),limit)
                (case/('native-arm'+str(ordinal)+'.'+suffix+'.private.bin')).write_bytes(raw)
        script('close_successful_current_model.py',common+['--case-plan',case/'plan.private.json','--out',closed],
            args.out/('close-'+str(current_case)+'.private.log'))
        result=load(closed/'result.private.json');need(result['completed'] and result['current_seven_restored_and_native_hashed'] and
            result['ordinary_exit_observed'] and not result['unknown_completion'],'Positive ordinary restore required before the next package')
        journal=(case/'native-stages.private.log').read_bytes()
        if args.scope=='P1':
            events=[list(map(int,r)) for r in re.findall(rb'P1_prefill_selected last_only=(\d+) tokens=(\d+) first_pos=(\d+) output_rows=(\d+)',journal)]
            exercised=len(events)==2 and all(r[1:3]==[30,0] and r[3]==(1 if r[0] else 30) for r in events)
        elif args.scope=='R1':
            events=[list(map(int,r)) for r in re.findall(rb'R1_token_ledger_closed request_end=(\d+) sync_requests=(\d+) actual_syncs=(\d+) close_rc=(-?\d+)',journal)]
            exercised=len(events)==3 and all(r[1]==22 and r[2]==(1 if r[0] else 22) and r[3]==0 for r in events)
        elif args.scope=='R1-direct':
            native=load(case/'passive-observer/native.private.bin')
            profile=load(package)['effective_application_policy']
            mode=profile['token_sync_policy'];need(mode in ('per_token','request_end'),'Explicit compiled ledger policy required')
            events=[[int(mode=='request_end'),r['token_ledger_records'],r['token_ledger_sync_calls'],
                     int(r['token_ledger_closed_before_request_result'])] for r in native['requests']]
            exercised=len(events)==3 and all(r[1]==22 and r[2]==(1 if r[0] else 22) and r[3]==1 for r in events)
            exercised=exercised and all(r['token_record_sync_policy']==mode and
                r['complete_request_span_ms']>=r['metrics']['total_ms'] and
                abs(r['complete_request_span_ms']-r['CPU_nested_calls_inclusive_exclusive_ns'][40]/1e6)<1
                for r in native['requests'])
        elif args.scope=='F32':
            events=[list(map(int,r)) for r in re.findall(rb'F32_request_completed request=(\d+) rows=(\d+) failures=(\d+)',journal)]
            rows=re.findall(rb'F32_row request=(\d+) row=(\d+) columns=(\d+) sha256=([0-9a-f]{64})',journal)
            exercised=events==[[1,23,0],[2,23,0],[3,23,0]] and len(rows)==69
            exercised=exercised and [(int(a),int(b),int(c)) for a,b,c,_ in rows]==\
                [(a,b,248320) for a in range(1,4) for b in range(1,24)]
        else:
            events=[list(map(int,r)) for r in re.findall(rb'G1_rank_scope events=(\d+) CPU_rank_calls=(\d+) CPU_checked_rows=(\d+) GPU_input_publications=(\d+) shadow_validation=(\d+) shadow_failures=(\d+) geometry_failures=(\d+) unsupported_variant=(\d+)',journal)]
            if args.scope=='G1-shadow':
                exercised=len(events)>=6 and events[-1][1]>0 and events[-1][2]>=events[-1][1] and all(r[3]==0 and r[4]==1 and r[5:]==[0,0,0] for r in events)
            else:
                exercised=len(events)>=6 and events[-1][3]>0 and all(r[1]==r[2]==0 and r[4]==0 and r[5:]==[0,0,0] for r in events)
        row=dict(case=current_case,package=record(package),case_plan=record(case/'plan.private.json'),
            close=record(closed/'result.private.json'),scope_events=events,all_intended_events_exercised=exercised,
            native_terminal=record(case/'passive-observer/native.private.bin'))
        save(args.out/('case-'+str(current_case)+'.complete.private.json'),row);records.append(row)
        print(json.dumps(dict(case=current_case,completed=True,current_restored=True,all_intended_events_exercised=exercised,events=events)),flush=True)
        need(exercised,'Scope effect was incomplete; original restored and remaining sequence stopped')
    save(args.out/'result.private.json',dict(completed=True,scope=args.scope,cases=records,automatic_retries=0,
        all_ordinary_closes_and_exact_restores=True,matched_analysis_still_required=True,production_adopted=False))


if __name__=='__main__':main()
