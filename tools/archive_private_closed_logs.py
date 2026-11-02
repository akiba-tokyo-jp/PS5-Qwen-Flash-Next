#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Archive then separately retire only the seventeen obsolete unreadable logs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import secrets
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import query
from run_successful_model_case import metadata
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,digest_expression,execute,lan_module


def observe(lan,plan,out,collect):
    if collect:
        need((out/'execution/execution.once.private.json').exists(),'Only collect the same submitted helper')
        if (out/'result.private.json').exists():
            result=load(out/'result.private.json');need(record(result['raw']['path'])==result['raw'],'Completed journal changed');return result
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=out/'collected-native.private.log';path.write_bytes(raw)
        return complete(lan,plan,out,raw,path)
    original=lan.web;expected='/fs'+urllib.parse.quote(plan['log'],safe='/')
    def bounded(path,limit=1<<20,timeout=15):return original(path,64<<20 if path==expected else limit,timeout)
    lan.web=bounded
    try:return execute(lan,plan,out,60)
    finally:lan.web=original


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','prior-archive','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage',choices=('export','retire'),required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true')
    p.add_argument('--execute-prepared',action='store_true',help='Submit only the exact reviewed, unlaunched export artifact')
    a=p.parse_args();need(sum((a.execute,a.collect,a.execute_prepared))<=1,'One submission or collection of the same helper')
    need(not a.execute_prepared or a.stage=='export','Prepared submission is limited to the read-only export phase')
    state=load(a.current/'active-console.private.json');need(state['original_restored'] and not state['native_running'] and
        not state['model_loaded'] and not state['unknown_completion'],'Positive idle current deployment required')
    prior=load(a.prior_archive);old=load(a.prior_archive.parent/'intent.private.json');selected=current_files(a.current)
    need(prior['completed'] and prior['PC_archive_preserved'] and prior['whole_native_and_PC_SHA256_verified_before_unlink'] and
         prior['all_selected_whole_SHA256_values_unchanged'],'Prior complete closed-case archive required')
    protected=old['protected'];need(len(protected)==108 and all(all(record(row['path'])[k]==row[k] for k in ('path','bytes','sha256')) for row in protected),
        'All selected108 whole-file identities must remain exact')
    protected_runs={state['active_successful_native_case']['run_id'],load(state['successful_route_20261102']['current_boot_model_proof']['case']['path'])['run_id'],
        state['successful_route_20261102']['current_boot_shader_CPU']['run_id']}
    for case in old['cases']:
        for key in ('case_plan','closed'):need(record(case[key]['path'])==case[key],'Positive closed case source changed')
        terminal=case['terminal'];need(all(record(terminal['path'])[k]==terminal[k] for k in ('path','bytes','sha256')),'Original terminal changed')
        closed=load(case['closed']['path']);native=load(terminal['path'])
        need(case['run_id'] not in protected_runs and closed['completed'] and closed['ordinary_exit_observed'] and not closed['unknown_completion'] and
            native['completed'] and native['all_model_source_device_owners_positively_retired'] and native['device_ledger_live_bytes']==0,
            'Only unprotected positively exited old owners are permitted')
    runs={case['run_id'] for case in old['cases']};targets=[]
    for item in old['unreadable_reports_preserved']:
        match=re.fullmatch(r'plan-([0-9a-f]{32})\.json\.driver\.log',item['name'])
        need(match and match[1] in runs and item['mode']=='-rw-------' and 0<item['bytes']<=1<<20,'Only exact obsolete0600 driver logs required')
        targets.append(dict(name=item['name'],remote=PHYSICAL+'/qwen-runtime/'+item['name'],alias=ALIAS+'/qwen-runtime/'+item['name'],bytes=item['bytes']))
    need(len(targets)==17 and len({row['remote'] for row in targets})==17 and sum(row['bytes'] for row in targets)<=2<<20,'Exact finite17-log scope required')
    need(len('CLOSED_LOG_BYTES ordinal=16 offset=1048575 hex=')+896+1<1024,'Every hex row must fit the actual1024-byte native journal formatter')
    lan=lan_module();folder=a.out/a.stage
    if a.collect or a.execute_prepared:
        intent=load(folder/'intent.private.json');need(intent['targets']==targets and intent['prior_archive']==record(a.prior_archive),'Consumed scope changed')
        plan=load(folder/'native/plan.private.json')
        if a.execute_prepared:
            need(not (folder/'native/execution/execution.once.private.json').exists(),'A consumed native scope is never submitted again')
            need(plan['operation']=='export-closed-logs' and plan['old_files']==plan['new_files']==selected,'Exact unchanged current-file guards required')
            for key in ('artifact','source','context','controller','project_source','exporter_source'):
                need(record(plan[key]['path'])==plan[key],'Reviewed prepared exporter input changed')
    else:
        folder.mkdir(parents=True,exist_ok=False)
        save(folder/'intent.private.json',dict(targets=targets,prior_archive=record(a.prior_archive),protected=protected,
            source_permission_changes=0,automatic_retries=0,stage=a.stage))
        if a.stage=='export':
            context='struct ClosedLog{const char*path;const char*alias;unsigned long long bytes;};\n'
            context+='#define CASE_CLOSED_LOG_COUNT 17u\n#define CASE_PRIOR_ARCHIVE_SHA256 '+json.dumps(record(a.prior_archive)['sha256'])+'\n'
            context+='static const struct ClosedLog case_closed_logs[]={'+','.join('{'+','.join((json.dumps(row['remote']),json.dumps(row['alias']),str(row['bytes'])+'ULL'))+'}' for row in targets)+'};\n'
            plan=build(a.workspace,a.mount_plan,selected,selected,[],'export-closed-logs',folder/'native',closed_log_export_context=context)
        else:
            exported=load(a.out/'export/result.private.json');need(exported['completed'] and exported['original_permissions_unchanged'] and exported['current_seven_native_hashed'],
                'All exact logs must first be independently archived after positive native completion')
            rows=exported['archives'];need(len(rows)==17 and all(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')} for row in rows),'All PC log archives must remain exact')
            need(all(row['remote']==target['remote'] and row['bytes']==target['bytes'] for row,target in zip(rows,targets)),'Exported scope differs')
            proof=dict(record(a.out/'export/result.private.json'),remote='/data/ai/moss-closed-log-proof-'+secrets.token_hex(16)+'.json')
            save(folder/'proof.private.json',proof)
            context='struct ClosedLogRetire{const char*path;const char*alias;unsigned long long bytes;const char*sha256;};\n'
            context+='static const struct ClosedLogRetire closed_logs[]={'+','.join('{'+','.join((json.dumps(row['remote']),json.dumps(row['alias']),str(row['bytes'])+'ULL',json.dumps(row['sha256'])))+'}' for row in rows)+'};\n'
            context+='static unsigned closed_log_index;static int closed_log_proof_checked;\n#define CASE_COMPLETED_FILE_KIND "archived_closed_log"\n#define CASE_COMPLETED_FILE_LABEL "ARCHIVED_CLOSED_LOG"\n'
            for key,field in (('PATH','path'),('ALIAS','alias'),('BYTES','bytes'),('SHA256','sha256')):context+='#define CASE_ACTIVATION_'+key+' closed_logs[closed_log_index].'+field+'\n'
            context+='static int case_completed_activation_reports_valid(void){if(!closed_log_proof_checked){if(!'+digest_expression(proof)+')return 0;closed_log_proof_checked=1;}return 1;}\n#include "activation_capture_retire.h"\n'
            context+='static int case_retire_completed_images(int*calls){for(closed_log_index=0;closed_log_index<17;++closed_log_index)if(!case_retire_activation(calls))return 0;return 1;}\n'
            plan=build(a.workspace,a.mount_plan,selected,selected,[],'retire-completed-images',folder/'native',completed_images_context=context)
        if not a.execute:return
        if a.stage=='retire':metadata(lan,[proof])
    result=observe(lan,plan,folder/'native',a.collect);need(result['completed'] and result['operation_calls']==17,'All exact CPU-only operations must complete and retire')
    if a.stage=='export':
        raw=Path(result['raw']['path']).read_bytes();archives=folder/'archives';archives.mkdir(exist_ok=True);values=[bytearray() for _ in targets];seals={}
        for line in raw.splitlines():
            match=re.fullmatch(rb'CLOSED_LOG_BYTES ordinal=(\d+) offset=(\d+) hex=([0-9a-f]+)',line)
            if match:
                index=int(match[1]);need(index<17 and int(match[2])==len(values[index]) and len(match[3])<=896,'Contiguous bounded archived log bytes required')
                values[index].extend(bytes.fromhex(match[3].decode('ascii')));need(len(values[index])<=targets[index]['bytes'],'Archive exceeds the exact source size')
            match=re.fullmatch(rb'CLOSED_LOG_SEALED ordinal=(\d+) bytes=(\d+) sha256=([0-9a-f]{64}) full_identity_and_EOF=1 original_mode=0600',line)
            if match:
                index=int(match[1]);need(index<17 and index not in seals,'One complete native seal per log');seals[index]=(int(match[2]),match[3].decode('ascii'))
        need(len(seals)==17 and b'CLOSED_LOG_EXPORT_COMPLETE count=17 original_permissions_unchanged=1 source_writes=0 GPU_calls=0\n' in raw,'Every log must seal positively')
        rows=[]
        for index,(data,target) in enumerate(zip(values,targets)):
            need(len(data)==target['bytes']==seals[index][0] and hashlib.sha256(data).hexdigest()==seals[index][1],'Independent complete PC/native log SHA differs')
            path=archives/target['name']
            if path.exists():need(path.read_bytes()==data,'A collected PC archive changed')
            else:path.write_bytes(data)
            rows.append(dict(record(path),remote=target['remote'],alias=target['alias']))
        save(folder/'result.private.json',dict(completed=True,archives=rows,bytes=sum(row['bytes'] for row in rows),native=record(folder/'native/result.private.json'),
            original_permissions_unchanged=True,source_writes=0,current_seven_native_hashed=True,GPU_calls=0,automatic_retries=0))
    else:
        proof=load(folder/'proof.private.json')
        with lan.ftplib.FTP() as ftp:
            ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('DELE '+proof['remote']).startswith(('226 ','250 ')),'Exact completed proof retirement failed')
        lan.absent(proof['remote']);vm=folder/'VM-after';vm.mkdir(exist_ok=False);observation=query(lan.HOST,vm)
        need(observation['boot_before']==observation['boot_after']==state['current_boot'],'Same boot required after ordinary cleanup')
        save(vm/'result.private.json',dict(completed=True,observations=observation,GPU_calls=0))
        save(folder/'result.private.json',dict(completed=True,archived_and_retired_console_logs=17,bytes=sum(row['bytes'] for row in targets),
            export=record(a.out/'export/result.private.json'),native=record(folder/'native/result.private.json'),VM_after=record(vm/'result.private.json'),
            original_directory_owner_restored=True,current_seven_native_hashed=True,PC_archives_preserved=True,source_permission_changes=0,proof_retired=True,GPU_calls=0,automatic_retries=0))
    need(all(all(record(row['path'])[key]==row[key] for key in ('path','bytes','sha256')) for row in protected),'Selected108 input changed')
    print(json.dumps(dict(completed=True,stage=a.stage,logs=17,bytes=sum(row['bytes'] for row in targets),source_permission_changes=0,GPU_calls=0)))


if __name__=='__main__':main()
