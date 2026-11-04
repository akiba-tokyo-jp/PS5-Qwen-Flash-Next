#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire one exact closed console trace after independent full PC verification."""
import argparse
import json
from pathlib import Path
import re
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,digest_expression,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','trace-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true');a=p.parse_args()
    need(not(a.execute and a.collect),'One once-only submission or collection phase required')
    proof=load(a.trace_proof)
    for key in ('case','raw','native_audit','closure'):need(record(proof[key]['path'])==proof[key],'Exported trace evidence changed')
    case_root=Path(proof['case']['path']).parent;case_path=case_root/'case/plan.private.json';case=load(case_path)
    terminal_path=case_root/'case/headless-observer/native.private.bin';terminal=load(terminal_path)
    audit=load(proof['native_audit']['path']);closed=load(proof['closure']['path']);state=load(a.current/'active-console.private.json')
    need(proof['completed'] and proof['all23_full_F32_rows_and_actual_routes_exact'] and
         terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         terminal['audit']==audit and audit['completed'] and audit['diagnostic_owners_positively_retired'] and
         closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Only a positively retired and ordinarily closed trace may be removed')
    need(state['active_successful_native_case']['run_id']!=case['run_id'],'The active/latest case is protected')
    latest=state['successful_route_20261102']['current_boot_model_proof']['case']
    need(Path(latest['path']).resolve()!=case_path.resolve(),'The latest completed real-model proof is protected')
    need(re.fullmatch(r'/app0/qwen-runtime/plan-[0-9a-f]{32}\.json\.pread-trace',audit['path']) and
         audit['path']==case['report']+'.pread-trace' and
         proof['raw']['bytes']==audit['bytes'] and proof['raw']['sha256']==audit['sha256'],
         'The exact independently whole-hashed bounded raw trace is required')
    current=current_files(a.current);reports=[dict(record(terminal_path),remote=PHYSICAL+case['report'][5:]),
        dict(proof['native_audit'],remote=PHYSICAL+case['report'][5:]+'.audit')]
    context='#define CASE_COMPLETED_FILE_KIND "model_pread_trace"\n#define CASE_COMPLETED_FILE_LABEL "MODEL_PREAD_TRACE"\n'
    context+='#define CASE_ACTIVATION_PATH '+json.dumps(PHYSICAL+audit['path'][5:])+'\n'
    context+='#define CASE_ACTIVATION_ALIAS '+json.dumps(ALIAS+audit['path'][5:])+'\n'
    context+='#define CASE_ACTIVATION_BYTES '+str(audit['bytes'])+'ULL\n#define CASE_ACTIVATION_SHA256 '+json.dumps(audit['sha256'])+'\n'
    context+='static int case_completed_activation_reports_valid(void){return '+'&&'.join(digest_expression(row) for row in reports)+';}\n'
    lan=lan_module()
    if a.collect:
        plan=load(a.out/'native/plan.private.json');need((a.out/'native/execution/execution.once.private.json').exists(),'Collect only a consumed native operation')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,a.out/'native',raw,path)
    else:
        a.out.mkdir(parents=True,exist_ok=False);save(a.out/'intent.private.json',dict(trace_proof=record(a.trace_proof),raw=proof['raw'],
            remote=PHYSICAL+audit['path'][5:],protected_current=current,PC_raw_preserved=True,recursive_operations=0))
        plan=build(a.workspace,a.mount_plan,current,current,[],'retire-activation',a.out/'native',activation_export_context=context)
        if not a.execute:return
        result=execute(lan,plan,a.out/'native')
    need(result['completed'] and result['operation_calls']==1,'One exact native unlink with restored directory ownership required')
    need(record(proof['raw']['path'])==proof['raw'],'The complete PC trace must remain exact')
    save(a.out/'result.private.json',dict(completed=True,retired_console_files=1,retired_bytes=audit['bytes'],
        both_namespaces_absent=True,whole_native_and_PC_SHA256_verified_before_unlink=True,
        current_seven_and_runtime_directory_owner_restored=True,PC_raw_preserved=True,latest_model_proof_protected=True,
        native=record(a.out/'native/result.private.json'),GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,retired_console_files=1,retired_bytes=audit['bytes'],GPU_calls=0)))


if __name__=='__main__':main()
