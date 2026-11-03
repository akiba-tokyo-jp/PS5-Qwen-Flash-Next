#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Archive and retire exact current-boot entry logs whose process IDs have exited."""
import argparse
import json
from pathlib import Path
import re
import secrets
import urllib.parse

from build_performance_quantizer import record
from run_successful_model_case import metadata
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,digest_expression,execute,lan_module


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--stage',choices=('handoff','archive','retire'),required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true');a=p.parse_args()
    need(not(a.execute and a.collect),'Submit once or collect the same operation')
    state=load(a.current/'active-console.private.json');need(state['original_restored'] and not state['native_running'] and
        not state['model_loaded'] and not state['unknown_completion'],'Positive idle restoration required')
    selected=current_files(a.current);lan=lan_module();folder=a.out/a.stage
    if a.stage=='handoff' and not a.collect:
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:processes=json.loads(response.read())['processes']
        live={int(row['pid']) for row in processes};need(not any(row['name']=='eboot.bin' for row in processes),'No application owner may remain')
        latest=load(state['successful_route_20261102']['current_boot_model_proof']['native_terminal']['path'])
        protected=live|{int(latest['pid'])};boot=state['current_boot'];lines=[]
        with lan.ftplib.FTP() as ftp:
            ftp.connect(lan.HOST,2121,timeout=20);ftp.login();ftp.retrlines('LIST '+PHYSICAL+'/qwen-runtime',lines.append)
        targets=[];preserved=[]
        pattern=re.compile('entry-b'+str(boot[0])+'-'+str(boot[1])+r'-(\d+)\.private\.log')
        for line in lines:
            fields=line.split(maxsplit=8)
            if len(fields)!=9:continue
            match=pattern.fullmatch(fields[8])
            if not match or int(match[1]) in protected:continue
            if not(fields[0]=='-rw-------' and fields[2]=='1' and fields[3]=='0' and 0<int(fields[4])<=1<<20):
                preserved.append(dict(name=fields[8],mode=fields[0],uid=fields[2],gid=fields[3],bytes=int(fields[4])));continue
            name=fields[8];targets.append(dict(name=name,pid=int(match[1]),bytes=int(fields[4]),
                remote=PHYSICAL+'/qwen-runtime/'+name,alias=ALIAS+'/qwen-runtime/'+name))
        targets.sort(key=lambda x:x['pid']);need(1<=len(targets)<=128 and sum(t['bytes'] for t in targets)<=64<<20,'Finite exited-owner log batch required')
        folder.mkdir(parents=True,exist_ok=False)
        save(a.out/'scope.private.json',dict(targets=targets,boot=boot,protected_PIDs=sorted(protected),processes_observed=processes,
            selected=selected,latest_model_terminal=state['successful_route_20261102']['current_boot_model_proof']['native_terminal'],
            original_file_mode='0600',owner_transition=[1,0],ineligible_logs_preserved=preserved,
            explicit_log_handling_authorized=True,recursive_operations=0))
        context='struct ClosedLog{const char*path;const char*alias;unsigned long long bytes;};\n'
        context+='#define CASE_CLOSED_LOG_COUNT '+str(len(targets))+'u\nstatic const struct ClosedLog case_closed_logs[]={'+','.join(
            '{'+','.join((json.dumps(t['remote']),json.dumps(t['alias']),str(t['bytes'])+'ULL'))+'}' for t in targets)+'};\n'
        original=(Path(__file__).resolve().parents[1]/'native/qwen_flash_next/closed_log_owner.h').read_text()
        for old,new in (('original[17]','original[CASE_CLOSED_LOG_COUNT]'),('CASE_CLOSED_LOG_COUNT!=17u','CASE_CLOSED_LOG_COUNT<1u||CASE_CLOSED_LOG_COUNT>128u'),
                        ('count=17 mode_changes','count='+str(len(targets))+' mode_changes')):
            need(original.count(old)==1,'Original qualified owner-handoff implementation changed');original=original.replace(old,new)
        context+=original
        plan=build(a.workspace,a.mount_plan,selected,selected,[],'retire-completed-images',folder/'native',completed_images_context=context)
        if not a.execute:return
    else:
        scope=load(a.out/'scope.private.json');targets=scope['targets'];need(scope['boot']==state['current_boot'] and scope['selected']==selected,'Boot or selected deployment changed')
        if a.stage=='handoff':plan=load(folder/'native/plan.private.json')
        else:
            handed=load(a.out/'handoff/result.private.json');need(handed['completed'] and handed['logs']==len(targets),'Positive exact metadata handoff required')
            if a.stage=='archive':
                need(not a.execute and not a.collect,'Archive performs only ordinary raw reads')
                folder.mkdir(exist_ok=False);rows=[]
                with lan.ftplib.FTP() as ftp:
                    ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw mode required')
                    for index,t in enumerate(targets):
                        path=folder/t['name'];size=0
                        with path.open('xb') as stream:
                            def write(block):
                                nonlocal size
                                size+=len(block);need(size<=t['bytes'],'Closed log exceeds its fixed extent');stream.write(block)
                            reply=ftp.retrbinary('RETR '+t['remote'],write,65536)
                        need(reply.startswith(('226 ','250 ')) and size==t['bytes'],'One complete returned raw log transfer required')
                        rows.append(dict(record(path),remote=t['remote'],alias=t['alias']));print(json.dumps(dict(archived=index+1,logs=len(targets))),flush=True)
                save(folder/'result.private.json',dict(completed=True,archives=rows,bytes=sum(t['bytes'] for t in targets),raw_reads_only=True,PS5_deletions=0))
                return
            archived=load(a.out/'archive/result.private.json');rows=archived['archives']
            need(archived['completed'] and len(rows)==len(targets) and all(record(r['path'])=={k:r[k] for k in ('path','bytes','sha256')} for r in rows),
                 'Every original log must first be fully preserved on PC')
            if a.collect:plan=load(folder/'native/plan.private.json')
            else:
                folder.mkdir(exist_ok=False);proof=dict(record(a.out/'archive/result.private.json'),remote='/data/ai/moss-entry-log-proof-'+secrets.token_hex(16)+'.json')
                save(folder/'proof.private.json',proof);metadata(lan,[proof])
                context='struct ArchivedLog{const char*path;const char*alias;unsigned long long bytes;const char*sha256;};\n'
                context+='static const struct ArchivedLog logs[]={'+','.join('{'+','.join((json.dumps(r['remote']),json.dumps(r['alias']),str(r['bytes'])+'ULL',json.dumps(r['sha256'])))+'}' for r in rows)+'};\n'
                context+='static unsigned log_index;static int proof_checked;\n#define CASE_COMPLETED_FILE_KIND "closed_entry_log"\n#define CASE_COMPLETED_FILE_LABEL "ENTRY_LOG"\n'
                for key,field in (('PATH','path'),('ALIAS','alias'),('BYTES','bytes'),('SHA256','sha256')):context+='#define CASE_ACTIVATION_'+key+' logs[log_index].'+field+'\n'
                context+='static int case_completed_activation_reports_valid(void){if(!proof_checked){if(!'+digest_expression(proof)+')return 0;proof_checked=1;}return 1;}\n#include "activation_capture_retire.h"\n'
                context+='static int case_retire_completed_images(int*calls){for(log_index=0;log_index<'+str(len(rows))+';++log_index)if(!case_retire_activation(calls))return 0;return 1;}\n'
                plan=build(a.workspace,a.mount_plan,selected,selected,[],'retire-completed-images',folder/'native',completed_images_context=context)
                if not a.execute:return
    if a.collect:
        need((folder/'native/execution/execution.once.private.json').exists(),'Collect only an already submitted operation')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=folder/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,folder/'native',raw,path)
    else:result=execute(lan,plan,folder/'native',60)
    need(result['completed'] and result['operation_calls']==len(targets),'Every exact metadata operation or retirement must positively return')
    save(folder/'result.private.json',dict(completed=True,logs=len(targets),bytes=sum(t['bytes'] for t in targets),
        native=record(folder/'native/result.private.json'),current_seven_native_hashed=True,GPU_calls=0,title_launches=0,
        initializer_requests=0,automatic_retries=0,stage=a.stage))
    if a.stage=='retire':
        proof=load(folder/'proof.private.json')
        with lan.ftplib.FTP() as ftp:
            ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('DELE '+proof['remote']).startswith(('226 ','250 ')),'Exact archive proof retirement required')
        lan.absent(proof['remote'])
    print(dict(completed=True,stage=a.stage,logs=len(targets),GPU_calls=0))


if __name__=='__main__':main()
