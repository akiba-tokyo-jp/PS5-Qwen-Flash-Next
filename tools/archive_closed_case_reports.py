#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Archive exact reports of positively closed cases, then retire console copies."""
import argparse
import json
from pathlib import Path
import re
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,digest_expression,execute,lan_module


def admitted_cases(batches,state,CPU_cases=()):
    cases=[]
    protected={state['active_successful_native_case']['run_id'],
        load(state['successful_route_20261102']['current_boot_model_proof']['case']['path'])['run_id'],
        state['successful_route_20261102']['current_boot_shader_CPU']['run_id']}
    for batch in batches:
        receipt=load(batch/'result.private.json')
        need(receipt['completed'] and receipt['GPU_calls']==0,'Completed exact image retirement required')
        for row in load(batch/'intent.private.json')['cases']:
            for key in ('case_record','case_plan','closed'):need(record(row[key]['path'])==row[key],'Closed-case evidence changed')
            closed=load(row['closed']['path']);case=load(row['case_plan']['path']);terminal=load(row['reports'][0]['path'])
            need(closed['completed'] and closed['ordinary_exit_observed'] and closed['current_seven_restored_and_native_hashed'] and
                not closed['unknown_completion'] and terminal['completed'] and terminal['all_model_source_device_owners_positively_retired'] and
                terminal['device_ledger_live_bytes']==0 and len(terminal['requests'])==3,'Positive ordinary completion required')
            need(re.fullmatch('[0-9a-f]{32}',case['run_id']) and case['run_id'] not in protected and
                case['report']=='/app0/qwen-runtime/plan-'+case['run_id']+'.json','Current native proof is protected')
            need(record(row['reports'][0]['path'])=={key:row['reports'][0][key] for key in ('path','bytes','sha256')},'Complete PC terminal changed')
            cases.append(dict(run_id=case['run_id'],terminal=row['reports'][0],case_plan=row['case_plan'],closed=row['closed'],pid=terminal['pid']))
    for root in CPU_cases:
        closed=load(root/'result.private.json');case=load(root/'plan.private.json')
        native=closed['native'];need(record(native['path'])==native,'Closed CPU result changed')
        terminal=load(native['path'])
        native_SHA=terminal.get('candidate_SELF_sha256',terminal.get('SELF_sha256'))
        need(closed['completed'] and closed['ordinary_exit_observed'] and closed['ordinary_close_calls']==1 and
             closed['current_seven_restored_and_native_hashed'] and closed['native_owners']==0 and not closed['unknown_completion'] and
             terminal['all_CPU_IO_returned'] and terminal['GPU_calls']==terminal['model_loads']==0 and
             terminal['run_id']==case['run_id'] and native_SHA==case['SELF']['sha256'],
             'Only positively returned, ordinarily closed CPU-only cases are admitted')
        need(re.fullmatch('[0-9a-f]{32}',case['run_id']) and case['run_id'] not in protected and
             case['report']=='/app0/qwen-runtime/plan-'+case['run_id']+'.json','Current CPU proof is protected')
        cases.append(dict(run_id=case['run_id'],terminal=dict(native,remote=PHYSICAL+case['report'][5:]),
            case_plan=record(root/'plan.private.json'),closed=record(root/'result.private.json'),pid=terminal['pid']))
    need(1<=len(cases)<=32 and len({row['run_id'] for row in cases})==len(cases),'Distinct bounded closed cases required')
    return cases


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--image-batch',type=Path,action='append',default=[])
    p.add_argument('--CPU-case',type=Path,action='append',default=[])
    p.add_argument('--execute',action='store_true');p.add_argument('--collect',action='store_true');a=p.parse_args()
    need(not(a.execute and a.collect),'Submit once or collect the same operation')
    state=load(a.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
        'Positive idle current deployment required')
    cases=admitted_cases(a.image_batch,state,a.CPU_case);current=current_files(a.current);lan=lan_module()
    selected=current+load(a.current/'provenance/retained-relink-inputs.private.json')
    package=load(a.current/'provenance/current-package.private.json');native=load(a.current/'provenance/native-link.receipt.private.json')
    selected+=native['formatter_stubs']+[package['formatter']]
    protected={Path(row['path']).resolve():record(row['path']) for row in selected}
    need(all(all(protected[Path(row['path']).resolve()][key]==row[key] for key in ('bytes','sha256')) for row in selected),'Selected inputs changed')
    if a.collect:
        intent=load(a.out/'intent.private.json');need(intent['cases']==cases,'Consumed retirement scope changed');targets=intent['targets']
        need(all(record(row['path'])=={key:row[key] for key in ('path','bytes','sha256')} for row in targets),'An archived report changed')
        plan=load(a.out/'native/plan.private.json');need((a.out/'native/execution/execution.once.private.json').exists(),'Only collect an existing operation')
        raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=a.out/'native/collected-native.private.log';path.write_bytes(raw)
        result=complete(lan,plan,a.out/'native',raw,path)
    else:
        a.out.mkdir(parents=True,exist_ok=False);archive=a.out/'archive';archive.mkdir();listing=[]
        with lan.ftplib.FTP() as ftp:
            ftp.connect(lan.HOST,2121,timeout=20);ftp.login();ftp.retrlines('LIST '+PHYSICAL+'/qwen-runtime',listing.append)
        (a.out/'directory-list.private.txt').write_text('\n'.join(listing)+'\n',encoding='utf-8',newline='\n')
        names={}
        for line in listing:
            fields=line.split(maxsplit=8)
            if len(fields)==9 and fields[0].startswith('-'):
                need(fields[8] not in names,'Duplicate directory entry');names[fields[8]]=fields
        targets=[];unreadable=[];boot=state['current_boot']
        for index,case in enumerate(cases):
            prefix='plan-'+case['run_id']+'.json';stage='entry-b'+str(boot[0])+'-'+str(boot[1])+'-'+str(case['pid'])+'.stages'
            chosen=sorted(name for name in names if name==prefix or name.startswith(prefix+'.') or name in (stage,'resident-launch-'+case['run_id']+'.json'))
            need(prefix in chosen and stage in chosen and len(chosen)<=128,'Exact completed case reports and final stage journal required')
            # Authenticate each case before deleting its main terminal last.
            chosen.remove(prefix);chosen.append(prefix)
            for name in chosen:
                fields=names[name];count=int(fields[4]);need(re.fullmatch('[A-Za-z0-9_.-]+',name) and 0<=count<=16<<20 and fields[2] in ('0','1') and fields[3]=='0','Bounded regular owned report required')
                if fields[0][7]!='r':
                    unreadable.append(dict(name=name,mode=fields[0],bytes=count,console_copy_preserved=True))
                    continue
                remote=PHYSICAL+'/qwen-runtime/'+name;raw=lan.web('/fs'+urllib.parse.quote(remote,safe='/'),max(1,count))
                need(len(raw)==count,'Full report export required');path=archive/name;path.write_bytes(raw)
                value=record(path)
                if name==prefix:need(all(value[key]==case['terminal'][key] for key in ('bytes','sha256')),'The native completed terminal differs from its original PC proof')
                targets.append(dict(value,remote=remote,alias=ALIAS+'/qwen-runtime/'+name,case_index=index))
        need(1<=len(targets)<=4096 and sum(row['bytes'] for row in targets)<=256<<20,'Finite explicit archive bound required')
        save(a.out/'intent.private.json',dict(cases=cases,targets=targets,unreadable_reports_preserved=unreadable,
            protected=list(protected.values()),PC_archive_preserved=True,recursive_operations=0))
        context='#include "closed_report_integrity.h"\n#define qwen_launch_digest_matches case_closed_report_digest\n'
        context+='struct ClosedReport{const char*path;const char*alias;unsigned long long bytes;const char*sha256;unsigned case_index;};\n'
        context+='static const struct ClosedReport closed_reports[]={'+','.join('{'+','.join([json.dumps(row['remote']),json.dumps(row['alias']),str(row['bytes'])+'ULL',json.dumps(row['sha256']),str(row['case_index'])])+'}' for row in targets)+'};\n'
        context+='static unsigned report_index;static unsigned char closed_case_admitted['+str(len(cases))+'];\n'
        context+='#define CASE_COMPLETED_FILE_KIND "closed_report"\n#define CASE_COMPLETED_FILE_LABEL "CLOSED_REPORT"\n'
        for key,field in (('PATH','path'),('ALIAS','alias'),('BYTES','bytes'),('SHA256','sha256')):context+='#define CASE_ACTIVATION_'+key+' closed_reports[report_index].'+field+'\n'
        context+='static int case_completed_activation_reports_valid(void){unsigned i=closed_reports[report_index].case_index;if(closed_case_admitted[i])return 1;switch(i){'
        for index,case in enumerate(cases):context+='case '+str(index)+':if(!'+digest_expression(case['terminal'])+')return 0;break;'
        context+='default:return 0;}closed_case_admitted[i]=1;return 1;}\n#include "activation_capture_retire.h"\n'
        context+='static int case_retire_completed_images(int*calls){for(report_index=0;report_index<'+str(len(targets))+';++report_index){if(!report("CLOSED_REPORT_TARGET ordinal=%u",report_index)||!case_retire_activation(calls))return 0;}return 1;}\n'
        plan=build(a.workspace,a.mount_plan,current,current,[],'retire-completed-images',a.out/'native',completed_images_context=context)
        if not a.execute:return
        original=lan.web;expected='/fs'+urllib.parse.quote(plan['log'],safe='/')
        def bounded_web(path,limit=1<<20,timeout=15):return original(path,64<<20 if path==expected else limit,timeout)
        lan.web=bounded_web
        try:result=execute(lan,plan,a.out/'native',observation_seconds=60)
        finally:lan.web=original
    need(result['completed'] and result['operation_calls']==len(targets),'All exact native retirements must positively complete')
    need(all(record(path)==value for path,value in protected.items()),'A selected input changed')
    save(a.out/'result.private.json',dict(completed=True,archived_and_retired_console_files=len(targets),bytes=sum(row['bytes'] for row in targets),
        PC_archive_preserved=True,whole_native_and_PC_SHA256_verified_before_unlink=True,both_console_namespaces_absent=True,
        original_runtime_directory_owner_restored=True,selected_files_protected=len(protected),all_selected_whole_SHA256_values_unchanged=True,
        latest_model_and_shader_CPU_proofs_protected=True,native=record(a.out/'native/result.private.json'),GPU_calls=0,title_launches=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,archived_and_retired_console_files=len(targets),bytes=sum(row['bytes'] for row in targets),selected_files_protected=len(protected),GPU_calls=0)))


if __name__=='__main__':main()
