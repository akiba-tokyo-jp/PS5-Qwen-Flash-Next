#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read the already accepted native owner; never launch or submit model work."""
import argparse
import json
from pathlib import Path
import urllib.error
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import lan_module,PHYSICAL


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-plan',type=Path,required=True);args=parser.parse_args()
    case=load(args.case_plan);out=args.case_plan.parent;launch=load(out/'launch/result.private.json')
    need(launch['completed'] and launch['operation_calls']==1 and launch['app_id']>0,'Already accepted ordinary launch required')
    lan=lan_module();remote=PHYSICAL+case['report'][5:]
    def get(path,limit=1<<20):
        try:return lan.web('/fs'+urllib.parse.quote(path,safe='/'),limit)
        except urllib.error.HTTPError as error:
            if error.code==404:return None
            raise
    def immutable(name,raw):
        target=out/name
        if target.exists():need(target.read_bytes()==raw,'Previously captured native evidence changed')
        else:target.write_bytes(raw)
    def complete_JSON(raw):
        if not raw or not raw.strip():return False
        try:json.loads(raw)
        except (json.JSONDecodeError,UnicodeDecodeError):return False
        return True
    first_raw=get(remote+'.first.start')
    if first_raw is None:
        state=dict(native_first_start_pending=True,automatic_retries=0)
        for suffix in ('failure','fatal'):
            raw=get(remote+'.'+suffix)
            if raw is not None and complete_JSON(raw):
                immutable('native.'+suffix+'.private.json',raw);state[suffix]=json.loads(raw)
        if 'failure' not in state and 'fatal' not in state:
            with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
                owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
            if len(owners)==1:
                pid=int(owners[0]['pid']);boot=load(case['model_proof']['path'])['current_boot']
                path=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(pid)+'.stages'
                raw=get(path,8<<20)
                if raw and raw.endswith(b'fatal_operation=main_SELF_Direct_integrity_returned_refusal\n'):
                    target=out/'early-boot-stages.private.log';target.write_bytes(raw)
                    observed=out/'host-early-self-refusal.private.json'
                    if not observed.exists():save(observed,dict(schema='ps5-qwen-host-observed-early-self-refusal-v1',
                        case_plan=record(args.case_plan),pid=pid,boot=boot,journal=dict(record(target),remote=path),
                        native_failure_JSON_present=False,source_audit_and_ordinary_close_still_required=True))
                    raise RuntimeError('Observed returned early SELF refusal; stop without replay and audit ordinary CPU close')
        print(json.dumps(state));return
    if not complete_JSON(first_raw):
        print(json.dumps(dict(native_first_start_pending=True,metadata_write_in_progress=True,observed_bytes=len(first_raw),automatic_retries=0)))
        return
    first=json.loads(first_raw);pid=first['pid']
    need(first['run_id']==case['run_id'] and first['candidate_SELF_sha256']==case['SELF']['sha256'],
         'Exact native run and linked SELF required')
    immutable('native-first-start.private.json',first_raw)
    proof=load(case['model_proof']['path']);boot=proof['current_boot']
    journal=PHYSICAL+'/qwen-runtime/entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(pid)+'.stages'
    stages=get(journal,8<<20)
    if stages is not None:(out/'native-stages.private.log').write_bytes(stages)
    state=dict(pid=pid,native_first_start_observed=True,automatic_retries=0,
        last_native_stage=stages.decode(errors='replace').splitlines()[-1] if stages else None)
    for suffix in ('failure','fatal'):
        raw=get(remote+'.'+suffix)
        if raw is not None and complete_JSON(raw):
            immutable('native.'+suffix+'.private.json',raw)
            state[suffix]=json.loads(raw)
    ready=get(remote+'.demo.ready')
    if ready is not None and complete_JSON(ready):
        immutable('native.demo.ready.private.json',ready);state['native_demo_ready']=True
    terminal=get(remote)
    if terminal is not None and complete_JSON(terminal):
        immutable('native.result.private.json',terminal);state['native_terminal_observed']=True
    with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
        owners=[r for r in json.loads(response.read())['processes'] if r['name']=='eboot.bin']
    need(len(owners)==1 and int(owners[0]['pid'])==pid,'Exact accepted title owner changed; no further requests')
    print(json.dumps(state))


if __name__=='__main__':main()
