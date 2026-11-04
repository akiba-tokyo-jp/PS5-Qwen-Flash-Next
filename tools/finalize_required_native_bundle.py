#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finalize one native-verified live input only after positive ordinary close."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL,ALIAS,digest_expression


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','case-plan','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    case=load(args.case_plan);terminal=load(args.case_plan.parent/'result.private.json')
    need(terminal['completed'] and terminal['required_bundle_restored'] and terminal['ordinary_exit_observed'] and
         terminal['current_original_restored'] and terminal['current_seven_file_native_hashes_pass'],
         'Positive original-byte copy, ordinary native close and exact selected restoration required')
    report_path=args.case_plan.parent/'native.required-bundle.private.json';report=load(report_path);scope=case['required_bundle_restore']['scope']
    need(report['completed'] and report['run_id']==case['run_id'] and report['scope']==scope and
         report['full_original_SHA256_and_EOF_readback'] and report['tracked_CPU_heap_free_returned'] and
         report['all_started_input_calls_returned'] and report['source_payloads_unchanged'] and report['GPU_calls']==0,
         'Exact full original native SHA and completed CPU owner required')
    identity=report['identity'];need(len(identity)==10 and identity[2]==0o100444 and identity[3] in (0,1) and identity[4]==0 and identity[5]==scope['bytes'],
        'Only the exact newly created read-only native-owned output may finalize')
    proof_record=case['required_bundle_restore']['current_model_proof'];need(record(proof_record['path'])==proof_record,'Current namespace proof changed')
    proof=load(proof_record['path'])
    remote=PHYSICAL+scope['path'][5:];alias=ALIAS+scope['path'][5:]
    need(re.fullmatch(re.escape(PHYSICAL)+r'/qwen-Q2-bundle-probe-[0-9a-f]{32}\.bin',remote),'Exact required output path required')
    report_remote=PHYSICAL+case['report'][5:]+'.required-bundle'
    context='#define CASE_BUNDLE_PATH '+json.dumps(remote)+'\n#define CASE_BUNDLE_ALIAS '+json.dumps(alias)+'\n'
    context+='#define CASE_BUNDLE_CANONICAL_DEVICE '+str(proof['canonical_directory'][0])+'ULL\n'
    context+='static const uint64_t case_bundle_native_identity[]={'+','.join(str(v)+'ULL' for v in identity)+'};\n'
    context+='static int case_completed_bundle_report_valid(void){return '+digest_expression(dict(record(report_path),remote=report_remote))+';}\n'
    old=current_files(args.current);plan=build(args.workspace,args.mount_plan,old,old,[],'finalize-bundle',args.out,finalize_context=context)
    if not args.execute:print('Exact completed bundle ownership finalization prepared; PS5 operations=0');return
    state_path=args.current/'active-console.private.json';state=load(state_path)
    need(state['original_restored'] and not state['native_running'] and not state['unknown_completion'],'Positively idle selected current application required')
    result=execute(lan_module(),plan,args.out);need(result['operation_calls'] in (0,1),'At most one exact owned metadata finalization is permitted')
    raw=(args.out/'execution/console.private.log').read_bytes();rows=re.findall(rb'COMPLETED_BUNDLE_ID component=(\d+) value=(\d+)',raw)
    if result['operation_calls']==1:need(b'RETURN owned_completed_bundle_owner_finalization rc=0 ' in raw,'Positive owner finalization return required')
    need(len(rows)==10 and [int(r[0]) for r in rows]==list(range(10)),'Complete fresh canonical native identity required')
    restored=dict(completed=True,path=remote,bytes=scope['bytes'],sha256=scope['sha256'],identity=[int(r[1]) for r in rows],
        full_native_original_SHA256_and_EOF_preserved=True,payload_writes=0,GPU_calls=0,title_launches=0,initializer_requests=0,
        native_copy_case=record(args.case_plan),native_report=record(report_path),finalization=record(args.out/'result.private.json'),
        identity_provider_symbol='Q2_'+scope['kind']+'_expected_identity')
    save(args.out/'restored-input.private.json',restored)
    state.setdefault('restored_required_bundle_inputs',[]).append(restored)
    for row in state.get('native_required_bundle_restorations',[]):
        if row['report']==restored['native_report']:
            row['root_ownership_finalization_pending']=False
            row['canonical_finalization']=restored['finalization']
    state['startup_bundle_repair']=dict(phase='native-copy-closed-original-bytes-and-root-owner-complete',result=record(args.out/'restored-input.private.json'))
    state_path.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(required_input_restored=True,kind=scope['kind'],bytes=scope['bytes'],original_whole_SHA256=True,
        current_original_restored=True,CPU_native_owner_retired=True,GPU_calls=0,payload_writes=0)))


if __name__=='__main__':main()
