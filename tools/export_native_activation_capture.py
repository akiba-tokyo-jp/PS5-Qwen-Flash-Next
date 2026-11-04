#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finalize readability of one positively sealed and ordinarily closed capture."""
import argparse
import json
from pathlib import Path
import re
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,execute,lan_module,digest_expression


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','closure','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--collect',action='store_true',help='Read the existing long journal and collect positive completion without submitting again')
    parser.add_argument('--retire-raw',action='store_true',help='Delete only the completed raw console stream after verified independent PC readback')
    parser.add_argument('--local-capture',type=Path,help='Completed PC readback receipt required for retirement')
    args=parser.parse_args();case=load(args.case_plan);closed=load(args.closure)
    state=load(args.current/'active-console.private.json');observer=args.case_plan.parent/'headless-observer'
    terminal=load(observer/'native.private.bin');capture=load(observer/'activation-capture.private.json')
    need(closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
         not closed['unknown_completion'] and state['original_restored'] and not state['native_running'] and not state['unknown_completion'],
         'One complete ordinary close and currently idle selected deployment required')
    need(terminal['completed'] and terminal['run_id']==case['run_id'] and terminal['candidate_SELF_sha256']==case['SELF']['sha256'] and
         terminal['all_model_source_device_owners_positively_retired'] and terminal['device_ledger_live_bytes']==0 and
         capture['completed'] and capture['full_native_SHA256_and_EOF_verified'] and capture['all_file_calls_returned'] and
         not capture['scratch_retained_until_ordinary_close'],'Exact positive native retirement and capture seal required')
    need(capture['path']==case['report']+'.activation-samples.bin' and
         re.fullmatch(r'/app0/qwen-runtime/plan-[0-9a-f]{32}\.json\.activation-samples\.bin',capture['path']) and
         16384<capture['bytes']<=256<<20 and re.fullmatch('[0-9a-f]{64}',capture['sha256']),
         'Only the exact unique bounded owned activation stream may be exported')
    if args.retire_raw:
        need(args.local_capture is not None,'A complete independent PC copy is required before retirement')
        local=load(args.local_capture)
        need(local['completed'] and local['native_and_host_whole_SHA256_equal'] and local['case']==record(args.case_plan) and
             local['capture']==record(observer/'activation-capture.private.json') and record(local['raw']['path'])==local['raw'] and
             local['raw']['sha256']==capture['sha256'] and local['raw']['bytes']==capture['bytes'],
             'The complete raw PC file must independently equal the positively sealed native stream')
    reports=[dict(record(observer/'native.private.bin'),remote=PHYSICAL+case['report'][5:]),
        dict(record(observer/'activation-capture.private.json'),remote=PHYSICAL+case['report'][5:]+'.activation-capture')]
    context='#define CASE_ACTIVATION_PATH '+json.dumps(PHYSICAL+capture['path'][5:])+'\n'
    context+='#define CASE_ACTIVATION_ALIAS '+json.dumps(ALIAS+capture['path'][5:])+'\n'
    context+='#define CASE_ACTIVATION_BYTES '+str(capture['bytes'])+'ULL\n#define CASE_ACTIVATION_SHA256 '+json.dumps(capture['sha256'])+'\n'
    context+='static int case_completed_activation_reports_valid(void){return '+'&&'.join(digest_expression(r) for r in reports)+';}\n'
    current=current_files(args.current)
    operation='retire-activation' if args.retire_raw else 'export-activation'
    if args.collect:
        plan=load(args.out/'native/plan.private.json')
        need(plan['operation']==operation and (args.out/'native/execution/execution.once.private.json').exists(),
             'Only the exact existing once-only CPU submission may be collected')
        lan=lan_module();raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20)
        path=args.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,args.out/'native',raw,path)
    else:
        args.out.mkdir(parents=True,exist_ok=False)
        plan=build(args.workspace,args.mount_plan,current,current,[],operation,args.out/'native',activation_export_context=context)
        result=execute(lan_module(),plan,args.out/'native')
    need(result['completed'] and result['operation_calls'] in (0,1),'One completed metadata finalization required')
    save(args.out/'result.private.json',dict(completed=True,case=record(args.case_plan),closure=record(args.closure),
        native_result=record(args.out/'native/result.private.json'),capture=record(observer/'activation-capture.private.json'),
        payload_writes=0,raw_stream_retired=bool(args.retire_raw),whole_SHA256_EOF_verified_before_retirement=bool(args.retire_raw),
        whole_SHA256_EOF_verified_both_namespaces=not args.retire_raw,mode=None if args.retire_raw else 420,helper_retired=True,
        GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,read_permission_published=not args.retire_raw,raw_stream_retired=bool(args.retire_raw),payload_writes=0,GPU_calls=0)))


if __name__=='__main__':main()
