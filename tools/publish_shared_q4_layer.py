#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Publish only new Q1 assets and seal complete bytes plus unchanged parent inputs."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import re
import secrets
import time
import urllib.parse

from build_performance_quantizer import record
from start_success_route import load,need,save
from success_case_control import ALIAS,PHYSICAL,build,complete,current_files,execute,lan_module


def finish(out,preparation,publication,result):
    prep=load(preparation);files=publication['files'];root=publication['directory'];application=publication['application_directory']
    raw=Path(result['raw']['path']).read_bytes()
    matches=re.findall(rb'SHARED_Q4_ID kind=(file|directory) index=(\d+) values=([0-9,]+)',raw)
    identities={int(i):list(map(int,v.split(b','))) for kind,i,v in matches if kind==b'file'}
    directory=[list(map(int,v.split(b','))) for kind,i,v in matches if kind==b'directory' and i==b'0']
    need(set(identities)==set(range(53)) and len(directory)==1 and all(len(v)==10 for v in identities.values()),
         'All complete new canonical identities are required')
    need(b'SHARED_Q4_SEALED new_files=53 complete_physical_and_alias_SHA256_EOF=1 parent_sources=518 parent_identities_and_directory_snapshots_unchanged=1 original_source_writes=0' in raw,
         'Complete new bytes and unchanged parent identities/snapshots required')
    observed=[dict(path=r['application'],bytes=r['local']['bytes'],sha256=r['local']['sha256'],identity=identities[i]) for i,r in enumerate(files)]
    seal=dict(schema='ps5-qwen-additional-shared-Q4-source-v1',model_receipt_sha256=prep['candidate']['sha256'],
        parent_model_receipt_sha256=prep['parent']['sha256'],source_directory=application,canonical_source_directory=root,
        directory_identity=directory[0],receipt_identity=identities[1],pack=observed[0],
        headers=[dict(r,file=PurePosixPath(r['path']).name) for r in observed[2:]],
        complete_physical_and_alias_SHA256_EOF=True,parent_518_identities_and_directory_snapshots_unchanged=True,
        original_source_writes=0,GPU_calls=0,title_launches=0,initializer_requests=0,mount_changes=0,automatic_retries=0)
    seal_path=out/'source-integrity.private.json';save(seal_path,seal)
    sealed=seal_path.read_text(encoding='utf-8');policy=dict(schema='ps5-qwen-additional-shared-Q4-source-policy-v1',
        raw=sealed,sha256=hashlib.sha256(sealed.encode()).hexdigest())
    save(out/'result.private.json',dict(completed=True,preparation=record(preparation),source_integrity=record(seal_path),
        policy=policy,native_result=record(out/'native/result.private.json'),new_files=53,source_writes=0,
        whole_new_bytes_and_all_parent_identities_qualified=True,model_inference=False,production_adopted=False))
    print(json.dumps(dict(completed=True,new_files=53,parent_source_identities=518,all_new_whole_SHA256_and_EOF=True,
        helper_positively_retired_and_removed=True,GPU_calls=0,original_source_writes=0,production_adopted=False)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','current','mount-plan','preparation','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--collect',action='store_true');args=parser.parse_args()
    if args.collect:
        publication=load(args.out/'plan.private.json');need(publication['preparation']==record(args.preparation),'Original preparation changed')
        plan=load(args.out/'native/plan.private.json')
        need(record(args.out/'native/plan.private.json')==publication['native_plan'] and
             (args.out/'native/execution/execution.once.private.json').exists(),'One existing durable submission required')
        lan=lan_module();raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20)
        target=args.out/'native/collected-console.private.log';target.write_bytes(raw)
        result=complete(lan,plan,args.out/'native',raw,target)
        finish(args.out,args.preparation,publication,result);return
    prep=load(args.preparation)
    need(prep['completed'] and prep['selected_tensors']==144 and prep['total_Q4_matrices']==253 and
         prep['prior_precision_layer_unchanged'] and prep['new_source_files']==53 and not prep['old_weight_packs_copied'],
         'The independently audited additional Q1 layer is required')
    inputs=[prep['pack'],prep['candidate'],*[{k:h[k] for k in ('path','bytes','sha256')} for h in prep['headers']]]
    need(all(record(r['path'])==r for r in inputs),'New Q1 assets changed')
    sources=load(args.current/'provenance/model-source-plan.private.json');parents=sources['physical']+sources['backing']
    need(sources['completed'] and len(parents)==518,'The complete selected parent source plan is required')
    args.out.mkdir(parents=True,exist_ok=False);nonce=secrets.token_hex(16);root=PHYSICAL+'/expert-q2-'+nonce
    alias=ALIAS+'/expert-q2-'+nonce;application='/app0/expert-q2-'+nonce
    files=[]
    for row in inputs:
        name=Path(row['path']).name
        need(re.fullmatch(r'(shared-q4\.bin|model-receipt\.json|qwen-flash-next-bf16-\d{5}-of-00076\.gguf)',name) is not None,
             'Only the explicit new Q1 filenames are admitted')
        files.append(dict(local=row,physical=root+'/'+name,alias=alias+'/'+name,application=application+'/'+name))
    need(len(files)==53 and len({r['physical'] for r in files})==53,'Exactly 53 distinct new Q1 assets required')
    context='#define SHARED_Q4_FILE_COUNT 53u\n#define SHARED_Q4_PARENT_COUNT 518u\n'
    context+='#define SHARED_Q4_DIRECTORY '+json.dumps(root)+'\n#define SHARED_Q4_ALIAS '+json.dumps(alias)+'\n'
    context+='struct shared_Q4_file{const char*physical,*alias;uint64_t bytes;const char*sha;};\n'
    context+='static const struct shared_Q4_file shared_Q4_files[]={'+','.join('{'+json.dumps(r['physical'])+','+
        json.dumps(r['alias'])+','+str(r['local']['bytes'])+'ULL,'+json.dumps(r['local']['sha256'])+'}' for r in files)+'};\n'
    context+='struct shared_Q4_parent{const char*physical,*alias;uint64_t expected[10];};\n'
    context+='static const struct shared_Q4_parent shared_Q4_parent_files[]={\n'
    directories=set()
    for row in parents:
        path=row['path'];need(path.startswith('/app0/') and '..' not in PurePosixPath(path).parts,'Exact parent source path required')
        physical=PHYSICAL+path[5:];mounted=ALIAS+path[5:];directories.add(str(PurePosixPath(physical).parent))
        context+='{'+json.dumps(physical)+','+json.dumps(mounted)+',{'+','.join(str(v)+'ULL' for v in row['identity'])+'}},\n'
    context+='};\n#define SHARED_Q4_DIRECTORY_COUNT '+str(len(directories))+'u\n'
    context+='static const char*shared_Q4_directories[]={'+','.join(map(json.dumps,sorted(directories)))+'};\n'
    old=current_files(args.current);plan=build(args.workspace,args.mount_plan,old,old,[],'seal-shared-Q4',args.out/'native',source_seal_context=context)
    publication=dict(completed=True,preparation=record(args.preparation),files=files,directory=root,
        application_directory=application,native_plan=record(args.out/'native/plan.private.json'),
        original_sources=record(args.current/'provenance/model-source-plan.private.json'),
        original_source_writes=0,maximum_submissions=1,automatic_retries=0,PS5_operations_started=False)
    save(args.out/'plan.private.json',publication)
    if not args.execute:print('New-only Q1 publication prepared; PS5 operations=0');return
    state=load(args.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'A positively completed idle native scope is required before publication')
    lan=lan_module();save(args.out/'upload-intent.private.json',dict(directory=root,files=files,automatic_retries=0))
    lan.absent(root)
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=30);ftp.login();need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw transfer mode required')
        reply=ftp.sendcmd('MKD '+root);save(args.out/'MKD-reply.private.json',dict(directory=root,reply=reply))
        need(reply.startswith(('226 ','250 ','257 ')),'New owned Q1 directory creation did not complete')
        for row in files:
            need(record(row['local']['path'])==row['local'],'Q1 input changed before upload');lan.absent(row['physical'])
            with Path(row['local']['path']).open('rb') as stream:reply=ftp.storbinary('STOR '+row['physical'],stream,65536)
            need(reply.startswith(('226 ','250 ')),'New Q1 file transfer did not complete')
    try:result=execute(lan,plan,args.out/'native')
    except RuntimeError:
        # Only collect the same durable one-shot submission. Never upload or
        # execute again because the host's initial deadline elapsed.
        if (args.out/'native/result.private.json').exists():raise
        submitted=args.out/'native/execution/execution.once.private.json'
        need(submitted.exists(),'No durable submitted native operation can be collected')
        deadline=time.monotonic()+600
        while True:
            raw=lan.web('/fs'+urllib.parse.quote(plan['log'],safe='/'),64<<20)
            if re.search(rb'\nEND success=\d+ operation_calls=\d+ app_id=-?\d+ log_healthy=\d+ GPU_calls=0 initializer_requests=0 mount_calls=0\n$',raw):
                late=args.out/'native/late-console.private.log';late.write_bytes(raw)
                result=complete(lan,plan,args.out/'native',raw,late);break
            need(time.monotonic()<deadline,'Same helper completion remains unknown; no replay');time.sleep(2)
    finish(args.out,args.preparation,publication,result)


if __name__=='__main__':main()
