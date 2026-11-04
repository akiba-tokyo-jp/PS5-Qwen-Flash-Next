#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind one known successful runtime setup to fresh pre-mount observations.

This does not mount or launch a title. It uses the unchanged qualified runtime,
requires its explicit ready return, and never retries a submitted initialization.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import query,review

ROOT=Path(__file__).resolve().parents[1]
RUNTIME_SHA='29760209bda40396f3453e5358674e9a15b4348c914abf40a4176206fe268120'
NAMES=('elfldr.elf','ftpsrv.elf','pldmgr.elf','shsrv.elf','websrv.elf','SceSysCore.elf','SceShellCore')
JOURNAL='/data/ai/logs/native-compat-setup-v1.log'


def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def need(value,message):
    if not value:raise RuntimeError(message)


def save(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush()
        import os
        os.fsync(stream.fileno())


def admission(observation):
    need(observation.get('completed') is True and observation.get('runtime_loaded') is False and
         observation.get('native_owners')==0 and observation.get('helper_exited') is True and
         observation.get('helper_files_removed') is True,'Complete pre-runtime observer required')
    rows=observation.get('success_route_prerequisites',[])
    need(len(rows)==2,'Both pre-mount snapshots required')
    for row in rows:
        need(row.get('firmware')==str(0x12400009) and row.get('title_mounts')=='0' and
             row.get('owned_mounts')=='0' and row.get('exact_title_alias')=='0' and
             row.get('source_directory')=='1' and row.get('page_size')=='16384' and row.get('reads_only')=='1',
             'Successful initialization-before-title-mount prerequisites differ')
    need(rows[0]['mount_fingerprint']==rows[1]['mount_fingerprint'],'Mount snapshots differ')
    expected={}
    for name in NAMES:
        found=[p for p in observation['processes'] if p['name']==name]
        need(len(found)==1 and found[0]['uid']=='0','Exact protected service identity required')
        expected[name]=int(found[0]['pid'])
    need(len(set(expected.values()))==7,'Protected service identities alias')
    return observation['boot'],expected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('workspace','cache','admission','out'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    observation=load(args.admission);boot,expected=admission(observation)
    raw=Path(observation['raw']['path']).read_bytes()
    need(record(observation['raw']['path'])==observation['raw'] and b'big_app=-1 query_only=1' in raw,
         'Complete observer bytes and absent foreground application required')
    manifest_path=args.workspace/'build/native-compat-setup-v1/manifest.json'
    manifest=load(manifest_path)
    inputs=manifest['loader_sources']+manifest['upstream_source_refs']+manifest['startup_inputs']+manifest['objects']
    inputs += [manifest[k] for k in ('release','extracted_public_kernel_payload','deployment_binary','audit','build_log')]
    for item in inputs:
        actual=record(item['path'])
        need(actual['bytes']==item['bytes'] and actual['sha256']==item['sha256'],
             'Known successful runtime input differs')
    binary=manifest['deployment_binary'];need(binary['bytes']==554264 and binary['sha256']==RUNTIME_SHA,'Known runtime identity differs')
    context=load(args.cache/'current/active-console.private.json')
    deployment=load(args.cache/'current/deployment.private.json')
    need(deployment['SELF']['sha256']=='56c29e9c871f5b068181675353c9098a4ff3513c29b00bb5dc4c1840897c0126','Current application differs')
    plan=dict(scope='fresh-successful-initialization-before-title-mount',
              authorization='Owner explicitly approved one kernel/ShellCore initialization after automatic-review refusal on 2026-11-02',
              admitted=record(args.admission),boot=boot,expected_services=expected,
              manifest=record(manifest_path),runtime=binary,
              source_inputs_verified=len({r['path'] for r in inputs}),
              old_boot_values_reused=False,runtime_requests_maximum=1,title_launches=0,mount_calls=0,GPU_calls=0,
              automatic_retries=0,original_application_replaced=False,
              successful_order='runtime ready, then separate title mount, then separate ordinary launch',
              runtime_memory_allowance_pages=1280,
              allowance_origin='Provisional software allowance: four 4MiB source arena slots plus loader and margin; not a measured peak bound')
    save(args.out/'plan.private.json',plan)
    if not args.execute:
        print(json.dumps(dict(prepared=True,source_inputs_verified=plan['source_inputs_verified'],console_operations=0)))
        return
    spec=importlib.util.spec_from_file_location('success_route_lan','D:/PS5-AI/moss/tools/live_moss_root_v1.py')
    lan=importlib.util.module_from_spec(spec);spec.loader.exec_module(lan)

    def processes():
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:
            return json.loads(response.read(1<<20))['processes']

    def same_services(allow_runtime=False):
        rows=processes()
        need(not any(p['name']=='eboot.bin' or 'shadowmount' in p['name'].lower() for p in rows),'Another application or mount owner is present')
        for name,pid in expected.items():need([int(p['pid']) for p in rows if p['name']==name]==[pid],'Protected service changed')
        if not allow_runtime:need(not any(p['name']=='payload' for p in rows),'A payload owner is already present')
        return rows

    same_services()
    vm=args.out/'VM-before';vm.mkdir();values=query(lan.HOST,vm)
    required=max(values['minimum'],values['reserved'])+1280
    verdict=review(values,boot,required)
    save(args.out/'VM-before.private.json',dict(values=values,required_pages=required,verdict=verdict))
    need(verdict['may_prepare_new_case'],'Runtime initialization software headroom policy refused; no request submitted')
    root='/data/ai/native-moss-image-sft/PPSA99190'
    protected=[dict(deployment['SELF'],remote=root+'/eboot.bin'),*deployment['application_files'],
               dict(deployment['shader_source_storage'],remote=root+'/qwen-runtime/'+Path(deployment['shader_source_storage']['path']).name)]
    verified=[]
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=20);ftp.login()
        need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Raw FTP mode not established')

        def digest(remote,size):
            ftp.voidcmd('TYPE I');need(ftp.size(remote)==size,'Remote file length differs')
            h=hashlib.sha256();received=0
            def consume(block):
                nonlocal received
                received+=len(block);need(received<=size,'Remote file exceeds its exact extent');h.update(block)
            ftp.retrbinary('RETR '+remote,consume,1<<18)
            need(received==size,'Remote file is short');return h.hexdigest()

        for row in protected:
            need(record(row['path'])=={k:row[k] for k in ('path','bytes','sha256')},'Current PC artifact differs')
            need(digest(row['remote'],row['bytes'])==row['sha256'],'Current PS5 artifact differs')
            verified.append({k:row[k] for k in ('remote','bytes','sha256')})
        save(args.out/'protected-files.private.json',dict(completed=True,files=verified))
        remote='/data/ai/bin/native-compat-setup-'+RUNTIME_SHA[:12]+'.elf'
        # This one unchanged binary is a required current-boot startup asset.
        # Never overwrite an existing different file or remove a resident loader.
        try:remote_size=ftp.size(remote)
        except lan.ftplib.error_perm as error:
            need(str(error).startswith('550'),'Runtime file state is unknown');remote_size=None
        if remote_size is None:
            with Path(binary['path']).open('rb') as stream:ftp.storbinary('STOR '+remote,stream,65536)
        need(digest(remote,binary['bytes'])==RUNTIME_SHA,'Remote runtime identity differs')
        try:old=lan.web('/fs'+urllib.parse.quote(JOURNAL,safe='/'),16384)
        except urllib.error.HTTPError as error:
            need(error.code==404,'Startup journal state is unknown');old=None
        if old is not None:
            previous=context['initializer_journal_recovered']
            need(len(old)==previous['bytes'] and hashlib.sha256(old).hexdigest()==previous['sha256'],
                 'Existing startup journal is not the recorded retired-boot file')
            begin=re.search(rb'BEGIN pid=\d+ unix_time=(\d+)',old)
            need(begin and int(begin[1])<boot[0],'Existing journal belongs to the current or unknown boot; never initialize again')
            (args.out/'retired-boot-journal.private.log').write_bytes(old)
            need(ftp.sendcmd('DELE '+JOURNAL).startswith(('226 ','250 ')),'Retired boot journal removal failed')
    try:
        lan.web('/fs'+urllib.parse.quote(JOURNAL,safe='/'),1)
    except urllib.error.HTTPError as error:
        need(error.code==404,'Startup journal absence is unknown')
    else:raise RuntimeError('Startup journal still exists; no initialization submitted')
    same_services()
    final_vm=args.out/'VM-final';final_vm.mkdir();final_values=query(lan.HOST,final_vm)
    final_required=max(final_values['minimum'],final_values['reserved'])+1280
    final_verdict=review(final_values,boot,final_required)
    save(args.out/'VM-final.private.json',dict(values=final_values,required_pages=final_required,verdict=final_verdict))
    need(final_verdict['may_prepare_new_case'],'Post-integrity headroom policy refused; no initialization submitted')
    request=dict(elf=remote,cwd='/data/ai',pipe='0')
    # The durable claim precedes the sole request. No exception path resubmits.
    save(args.out/'initialization.once.private.json',dict(plan=record(args.out/'plan.private.json'),request=request,
                                                        max_requests=1,automatic_retries=0))
    try:
        response=lan.web('/elfldr?'+urllib.parse.urlencode(request),65536,8)
        (args.out/'dispatch-response.private.bin').write_bytes(response)
    except Exception as error:save(args.out/'dispatch-uncertain.private.json',dict(error_type=type(error).__name__,resubmitted=False))
    deadline=time.monotonic()+45;terminal=None
    while time.monotonic()<deadline:
        try:
            raw=lan.web('/fs'+urllib.parse.quote(JOURNAL,safe='/'),16384,8)
            (args.out/'runtime.private.log').write_bytes(raw)
            if b'\nEND ' in raw:terminal=raw;break
        except Exception as error:
            save_path=args.out/'first-monitor-error.private.json'
            if not save_path.exists():save(save_path,dict(error_type=type(error).__name__,resubmitted=False))
        time.sleep(1)
    need(terminal is not None,'Runtime ready return unknown; stop all further execution, never retry')
    need(b'RETURN upstream_kernel_entry payload_result=0 KEKCALL_CHECK_loaded=1 raw=0x0 carry=0' in terminal and
         b'status=compatibility_reported_ready loader_resident=1' in terminal,'Runtime did not positively report ready; no title launch')
    begin=re.search(rb'BEGIN pid=(\d+) unix_time=(\d+)',terminal)
    need(begin and int(begin[2])>=boot[0],'Fresh runtime journal required')
    pid=int(begin[1]);rows=same_services(True)
    need([int(p['pid']) for p in rows if p['name']=='payload']==[pid],'Exact resident runtime owner required')
    result=dict(completed=True,scope=plan['scope'],boot=boot,runtime_pid=pid,runtime_loaded=True,
                positive_kernel_entry_return=True,known_runtime_SHA256=RUNTIME_SHA,protected_files_verified=7,
                runtime_requests=1,automatic_retries=0,mount_calls=0,title_launches=0,GPU_calls=0,
                runtime_resident_by_design=True,journal=record(args.out/'runtime.private.log'))
    save(args.out/'result.private.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('boot','runtime_pid','journal')}))


if __name__=='__main__':main()
