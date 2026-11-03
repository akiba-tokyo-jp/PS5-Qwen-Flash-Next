#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Join positively staged owned files with bounded native Direct I/O, then retire inputs."""
import argparse
import json
from pathlib import Path
import re
from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('workspace','current','mount-plan','staging-plan','stream-controls','integrity-controls','out'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--staging-result',type=Path);p.add_argument('--execute',action='store_true')
    a=p.parse_args();staging,stream,integrity=map(load,(a.staging_plan,a.stream_controls,a.integrity_controls))
    need(stream['completed'] and stream['positive_controls']==8 and stream['negative_controls']==15 and
         stream['PS5_operations']==0 and all(record(r['path'])==r for r in stream['inputs']),
         'The new nonaligned-part, tail, partial-I/O and close controls must pass')
    need(integrity['completed'] and integrity['whole_integrity_window_bytes']==262144,
         'Reuse the already qualified larger Direct whole-file integrity window')
    rows=staging['parts'];fragment=staging['fragment']
    need(len(rows)==4 and fragment['bytes']==sum(r['local']['bytes'] for r in rows)==27033600 and
         len({r['remote'] for r in rows})==4 and all(re.fullmatch(r'/data/ai/moss-qwen-case-[0-9a-f]{32}-candidate-SELF\.bin',r['remote']) for r in rows),
         'Exactly the four owned new fragment inputs are required')
    selected=current_files(a.current)
    if not a.execute:
        import secrets
        a.out.mkdir(parents=True,exist_ok=False)
        target='/data/ai/moss-qwen-case-'+secrets.token_hex(16)+'-candidate-SELF.bin'
        context='#define CONCAT_TARGET '+json.dumps(target)+'\n#define CONCAT_BYTES '+str(fragment['bytes'])+'ULL\n'
        context+='#define CONCAT_SHA256 '+json.dumps(fragment['sha256'])+'\n#define CONCAT_PARTS {'+','.join(
            '{'+json.dumps(r['remote'])+','+str(r['local']['bytes'])+'ULL,'+json.dumps(r['local']['sha256'])+'}' for r in rows)+'}\n'
        plan=build(a.workspace,a.mount_plan,selected,selected,[],'concatenate-model-parts',a.out/'native',concat_context=context)
        need(plan['CPU_metadata_margin_pages']==68 and plan['minimum_live_free_pages']==1201 and
             plan['additional_fixed_CPU_buffer_pages']==47 and not plan['CPU_control_independent_thresholds'],
             'Both buffers, larger integrity window and stronger original CPU floor must be charged')
        save(a.out/'intent.private.json',dict(staging_plan=record(a.staging_plan),parts=rows,fragment=fragment,target=target,
            selected=selected,stream_controls=record(a.stream_controls),integrity_controls=record(a.integrity_controls),
            native_plan=record(a.out/'native/plan.private.json'),source_headers=[plan['concat_source'],plan['stream_source']],
            input_deletion_only_after_whole_SHA256_and_helper_exit=True,original_source_writes=0,automatic_retries=0,
            CPU_deadline_seconds=30,maximum_live_copy_buffer_bytes=524288,whole_integrity_window_bytes=262144))
        print(json.dumps(dict(prepared=True,bytes=fragment['bytes'],PS5_operations=0)));return
    need(a.staging_result is not None,'The actual four positive FTP completions are required')
    done=load(a.staging_result);intent=load(a.out/'intent.private.json')
    need(done['completed'] and done['all_FTP_calls_returned'] and done['all_host_file_and_socket_handles_closed'] and
         done['parts']==rows==intent['parts'] and done['fragment']==fragment==intent['fragment'] and
         intent['staging_plan']==record(a.staging_plan) and intent['selected']==selected and
         intent['stream_controls']==record(a.stream_controls) and intent['integrity_controls']==record(a.integrity_controls) and
         all(record(r['path'])==r for r in intent['source_headers']),
         'Only the same prepared inputs and four completed ordinary stores may execute')
    state=load(a.current/'active-console.private.json');need(state['original_restored'] and not state['native_running'] and
        not state['model_loaded'] and not state['unknown_completion'],'One positively idle console required')
    need(record(intent['native_plan']['path'])==intent['native_plan'],'The exact bounded native helper changed')
    plan=load(intent['native_plan']['path']);lan=lan_module()
    need(not(a.out/'native/execution/execution.once.private.json').exists(),'Never repeat a consumed concatenation')
    result=execute(lan,plan,a.out/'native',60)
    raw=Path(result['raw']['path']).read_bytes()
    parts=re.findall(rb'CONCAT_PART index=(\d+) SHA256=1 identity_exact=1 fd_closed=1',raw)
    need(result['completed'] and result['helper_exited'] and list(map(int,parts))==list(range(4)) and
         re.search(rb'CONCAT_COMPLETE success=1 .* closed_parts=4 target_closed=1 whole_SHA256_EOF=1 original_source_writes=0 GPU_calls=0',raw),
         'Every source identity, hash, descriptor and whole output must complete before removing inputs')
    save(a.out/'positive-output-before-input-retirement.private.json',dict(completed=True,target=intent['target'],fragment=fragment,
        native=record(a.out/'native/result.private.json'),helper_exited=True,all_input_descriptors_positively_closed=True))
    save(a.out/'input-retirement.once.private.json',dict(inputs=[r['remote'] for r in rows],output=intent['target']))
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=30);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw cleanup mode required')
        for row in rows:need(ftp.sendcmd('DELE '+row['remote']).startswith(('226 ','250 ')),'Positive owned input removal required')
    for row in rows:lan.absent(row['remote'])
    save(a.out/'result.private.json',dict(completed=True,fragment=fragment,remote=intent['target'],immutable_mode=292,
        native=record(a.out/'native/result.private.json'),whole_SHA256_and_EOF=True,all_four_input_files_removed=True,
        all_source_and_target_descriptors_positively_closed=True,helper_exited=True,helper_files_removed=True,
        staging=record(a.staging_result),current_seven_unchanged=True,source_publication_still_required=True,
        original_source_writes=0,title_launches=0,GPU_calls=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,bytes=fragment['bytes'],inputs_removed=4,title_launches=0,GPU_calls=0)))


if __name__=='__main__':main()
