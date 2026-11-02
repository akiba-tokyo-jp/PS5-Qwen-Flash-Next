#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish one new bounded immutable operator pack without changing current files."""
import argparse
import json
from pathlib import Path
import re
import secrets
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,execute,lan_module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','profile','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--collect',action='store_true')
    parser.add_argument('--submit-prepared',action='store_true',help='First submission of a prepared artifact that failed host validation before any once-only marker')
    args=parser.parse_args();need(not(args.collect and args.submit_prepared),'One explicit publication phase required');profile=load(args.profile)
    need(profile['completed'] and profile['kind']=='Q2-IQ2-fixture' and profile['unloaded_GPU_fixture'],
         'Only an explicitly compiled unloaded operator pack may be published')
    pack=profile['component_pack'];local=pack['local'];application=pack['application_path']
    need(record(local['path'])==local and local['bytes']<=16<<20 and
         re.fullmatch(r'/app0/qwen-runtime/iq2-Up-[0-9a-f]{24}\.bin',application) and
         local['sha256'][:24] in application,'One exact small content-bound component path is required')
    state=load(args.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Positively completed idle current deployment required')
    lan=lan_module()
    if args.collect or args.submit_prepared:
        publication=load(args.out/'plan.private.json');need(publication['profile']==record(args.profile),'The original scoped profile changed')
        plan=load(args.out/'native/plan.private.json')
        need(plan['operation']=='publish-component' and record(plan['artifact']['path'])==plan['artifact'],'The exact prepared CPU artifact is required')
        marker=args.out/'native/execution/execution.once.private.json'
        if args.collect:
            need(marker.exists(),'One existing consumed CPU publication is required')
            raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20);path=args.out/'native/collected-native.private.log';path.write_bytes(raw)
            result=complete(lan,plan,args.out/'native',raw,path)
        else:
            need(not marker.exists() and not(args.out/'native/result.private.json').exists(),
                 'An operation with a durable submission marker or terminal result must never be resubmitted')
            lan.absent(plan['remote']);lan.absent(plan['log']);lan.absent(plan['claim'])
            result=execute(lan,plan,args.out/'native',observation_seconds=60)
    else:
        args.out.mkdir(parents=True,exist_ok=False);pending='/data/ai/moss-qwen-case-'+secrets.token_hex(16)+'-IQ2-component.bin'
        target=PHYSICAL+application[5:];alias=ALIAS+application[5:]
        lan.absent(pending);lan.absent(target)
        save(args.out/'upload.once.private.json',dict(local=local,pending=pending,target=target,automatic_retries=0))
        with lan.ftplib.FTP() as ftp:
            ftp.connect(lan.HOST,2121,timeout=20);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw transfer mode required')
            with Path(local['path']).open('rb') as stream:reply=ftp.storbinary('STOR '+pending,stream,65536)
            need(reply.startswith(('226 ','250 ')) and ftp.size(pending)==local['bytes'],'One complete bounded pending upload required')
        context='#define CASE_COMPONENT_PENDING '+json.dumps(pending)+'\n#define CASE_COMPONENT_TARGET '+json.dumps(target)+'\n'
        context+='#define CASE_COMPONENT_ALIAS '+json.dumps(alias)+'\n#define CASE_COMPONENT_BYTES '+str(local['bytes'])+'ULL\n'
        context+='#define CASE_COMPONENT_SHA256 '+json.dumps(local['sha256'])+'\n'
        current=current_files(args.current)
        plan=build(args.workspace,args.mount_plan,current,current,[],'publish-component',args.out/'native',component_publish_context=context)
        save(args.out/'plan.private.json',dict(profile=record(args.profile),pack=local,target=target,alias=alias,pending=pending,
            native_plan=record(args.out/'native/plan.private.json')))
        result=execute(lan,plan,args.out/'native',observation_seconds=60)
    need(result['completed'] and result['operation_calls']==1,'One positively completed new-only publication required')
    save(args.out/'result.private.json',dict(completed=True,profile=record(args.profile),pack=local,
        native_result=record(args.out/'native/result.private.json'),whole_physical_and_alias_SHA256_EOF=True,immutable_mode=292,
        original_runtime_directory_owner_restored=True,current_seven_unchanged_and_native_hashed=True,
        helper_retired=True,title_launches=0,GPU_calls=0,initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,new_immutable_component_files=1,whole_SHA256_both_namespaces=True,current_seven_unchanged=True,GPU_calls=0)))


if __name__=='__main__':main()
