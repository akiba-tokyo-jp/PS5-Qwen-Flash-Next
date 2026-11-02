#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Transfer17 positively closed obsolete logs to their private archive reader."""
import argparse
import json
from pathlib import Path
import re

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import build,current_files,execute,lan_module,PHYSICAL,ALIAS

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','archive','returned-open','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    state=load(a.current/'active-console.private.json');need(state['original_restored'] and not state['native_running'] and
        not state['model_loaded'] and not state['unknown_completion'],'Positive idle current deployment required')
    archived=load(a.archive);old=load(a.archive.parent/'intent.private.json');refused=load(a.returned_open)
    need(archived['completed'] and archived['all_selected_whole_SHA256_values_unchanged'] and
         refused['helper_exited'] and refused['helper_files_removed'] and not refused['completed'] and
         record(refused['raw']['path'])==refused['raw'],'Positive closed archive and returned descriptor refusal required')
    raw=Path(refused['raw']['path']).read_bytes()
    need(re.findall(rb'DESCRIPTOR_OPEN index=(\d+) fd=-1 errno=13',raw)==[b'0',b'1'],
         'Exact native physical/alias EACCES observation required')
    protected=old['protected'];need(len(protected)==108 and all(record(r['path'])==r for r in protected),'All108 selected inputs required')
    active={state['active_successful_native_case']['run_id'],state['successful_route_20261102']['current_boot_shader_CPU']['run_id'],
        load(state['successful_route_20261102']['current_boot_model_proof']['case']['path'])['run_id']}
    runs=set()
    for c in old['cases']:
        need(c['run_id'] not in active and all(record(c[k]['path'])==c[k] for k in ('case_plan','closed')),'Only unprotected immutable closed cases required')
        closed=load(c['closed']['path']);need(closed['completed'] and closed['ordinary_exit_observed'] and not closed['unknown_completion'],'Positive old process exit required')
        runs.add(c['run_id'])
    targets=[]
    for r in old['unreadable_reports_preserved']:
        m=re.fullmatch(r'plan-([0-9a-f]{32})\.json\.driver\.log',r['name'])
        need(m and m[1] in runs and r['mode']=='-rw-------' and 0<r['bytes']<=1<<20,'Only exact obsolete logs required')
        targets.append(dict(name=r['name'],remote=PHYSICAL+'/qwen-runtime/'+r['name'],alias=ALIAS+'/qwen-runtime/'+r['name'],bytes=r['bytes']))
    need(len(targets)==17 and sum(r['bytes'] for r in targets)==1161178,'Exact17-log batch required')
    a.out.mkdir(parents=True,exist_ok=False)
    context='struct ClosedLog{const char*path;const char*alias;unsigned long long bytes;};\n#define CASE_CLOSED_LOG_COUNT 17u\n'
    context+='static const struct ClosedLog case_closed_logs[]={'+','.join('{'+','.join((json.dumps(r['remote']),json.dumps(r['alias']),str(r['bytes'])+'ULL'))+'}' for r in targets)+'};\n'
    header=ROOT/'native/qwen_flash_next/closed_log_owner.h';context+=header.read_text(encoding='utf-8')
    rows=current_files(a.current)
    # The historical completed-file adapter also supports metadata-only work.
    # This context contains chown and lstat, with no source unlink/open/read API.
    plan=build(a.workspace,a.mount_plan,rows,rows,[],'retire-completed-images',a.out/'native',completed_images_context=context)
    save(a.out/'intent.private.json',dict(targets=targets,protected=protected,source=record(header),prior_archive=record(a.archive),
        descriptor_refusal=record(a.returned_open),owner_transition=[1,0],old_and_new_mode='0600',owner_changes=17,
        payload_writes=0,mode_changes=0,explicit_log_handling_permission_received=True,automatic_retries=0))
    if not a.execute:return
    result=execute(lan_module(),plan,a.out/'native',60)
    need(result['completed'] and result['operation_calls']==17 and result['helper_exited'] and result['helper_files_removed'],'All exact owner transfers must positively complete')
    need(all(record(r['path'])==r for r in protected),'Selected108 inputs changed')
    save(a.out/'result.private.json',dict(completed=True,logs=17,bytes=1161178,owner_changes=17,new_uid=0,mode='0600',payload_writes=0,
        original_payload_mtime_inode_and_size_preserved=True,current_seven_native_hashed=True,all108_PC_inputs_exact=True,
        native=record(a.out/'native/result.private.json'),GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,owner_changes=17,mode='0600',GPU_calls=0)))


if __name__=='__main__':main()
