#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Retire the exact53 disjoint new Q1 files after a completed negative comparison."""
import argparse
import hashlib
import json
from pathlib import Path,PurePosixPath
import urllib.parse

from build_performance_quantizer import record
from kernel_vm_preflight import query
from start_success_route import load,need,save
from success_case_control import PHYSICAL,current_files,lan_module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('current','publication','analysis','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--collect-deleted-first',action='store_true',help='Collect the single returned226 deletion that ftplib.delete rejected; never resubmit it')
    args=parser.parse_args();state=load(args.current/'active-console.private.json')
    need(state['original_restored'] and not state['native_running'] and not state['model_loaded'] and not state['unknown_completion'],
         'Positively completed idle current deployment required')
    analysis=load(args.analysis);need(analysis['completed'] and analysis['scope']=='Q1' and analysis['native_requests']==12 and
         analysis['all_ordinary_closes_and_exact_restores'],'The complete closed Q1 comparison is required')
    disposition=load(Path(__file__).resolve().parents[1]/'docs/native-performance-comparisons-20261102.json')
    need(disposition['Q1']['status']=='measured_profile_not_adopted','The measured Q1 disposition must reject adoption')
    publication=load(args.publication);need(publication['completed'] and publication['new_files']==53,'Complete new-only publication required')
    seal=load(publication['source_integrity']['path']);need(record(publication['source_integrity']['path'])==publication['source_integrity'],'Q1 source seal changed')
    original=load(args.publication.parent/'plan.private.json');files=original['files'];root=original['directory']
    need(root==seal['canonical_source_directory'] and root.startswith(PHYSICAL+'/expert-q2-') and len(files)==53,
         'Only the exact previously sealed new directory is allowed')
    paths=[r['physical'] for r in files];names=[PurePosixPath(p).name for p in paths]
    need(len(set(paths))==53 and all(str(PurePosixPath(p).parent)==root and '..' not in PurePosixPath(p).parts for p in paths),
         'All53 targets must be direct children of the exact owned directory')
    parents=load(args.current/'provenance/model-source-plan.private.json')
    required=load(args.current/'provenance/required-bundle-inputs.private.json')
    protected=current_files(args.current)
    need(root not in json.dumps([parents,required,protected,load(args.current/'qwen-runtime/development.json')]),
         'A selected production input references the proposed retirement root')
    if args.collect_deleted_first:
        prior=load(args.out/'intent.private.json')
        need(prior['publication']==record(args.publication) and prior['analysis']==record(args.analysis) and prior['files']==paths and
             not list(args.out.glob('removed-*.private.json')),'Only the exact first returned deletion can be collected here')
    else:args.out.mkdir(parents=True,exist_ok=False)
    lan=lan_module()
    def idle():
        with lan.OPENER.open('http://'+lan.HOST+':8084/processes_list',timeout=8) as response:rows=json.loads(response.read())['processes']
        need(not any(r['name']=='eboot.bin' for r in rows),'An application owner is present; stop retirement')
    def verify(rows):
        results=[]
        for row in rows:
            digest=hashlib.sha256();size=0
            url='http://'+lan.HOST+':8080/fs'+urllib.parse.quote(row['remote'],safe='/')
            with lan.OPENER.open(url,timeout=30) as response:
                while block:=response.read(1<<20):
                    size+=len(block);need(size<=row['bytes'],'Protected file exceeded its exact length');digest.update(block)
            need(size==row['bytes'] and digest.hexdigest()==row['sha256'],'Protected current file changed')
            results.append(dict(remote=row['remote'],bytes=size,sha256=digest.hexdigest()))
        return results
    def listing(ftp):
        lines=[];ftp.retrlines('LIST '+root,lines.append)
        values=[line.split(None,8)[-1] for line in lines];return sorted(n for n in values if n not in ('.','..'))
    idle();before=verify(protected)
    vm=args.out/('VM-collected' if args.collect_deleted_first else 'VM-before');vm.mkdir();values=query(lan.HOST,vm)
    need(values['boot_before']==values['boot_after']==state['current_boot'],'Boot changed before maintenance')
    if not args.collect_deleted_first:
        save(args.out/'intent.private.json',dict(publication=record(args.publication),analysis=record(args.analysis),
            root=root,files=paths,protected_seven=before,protected_parent_sources=518,protected_required_bundle_inputs=69,
            VM_before=values,automatic_retries=0,recursive_deletion=False))
    else:need(before==prior['protected_seven'],'Current files changed since the first returned deletion')
    with lan.ftplib.FTP() as ftp:
        ftp.connect(lan.HOST,2121,timeout=20);ftp.login()
        need(ftp.sendcmd('SELF')=='226 SELF transfer mode disabled','Exact raw FTP mode required')
        start=1 if args.collect_deleted_first else 0
        if start:
            lan.absent(paths[0])
            save(args.out/'removed-0.private.json',dict(path=paths[0],reply='226 File deleted',
                original_ftplib_delete_rejected_positive_reply=True,read_only_absence_confirmed=True,resubmitted=False))
        need(listing(ftp)==sorted(names[start:]),'The new directory contains files outside the exact manifest')
        for row in files[start:]:
            need(ftp.size(row['physical'])==row['local']['bytes'],'A sealed candidate file size changed')
        idle()
        for index,path in enumerate(paths[start:],start):
            reply=ftp.sendcmd('DELE '+path);need(reply.startswith(('226 ','250 ')),'One exact candidate file deletion did not complete')
            save(args.out/('removed-'+str(index)+'.private.json'),dict(path=path,reply=reply))
        need(not listing(ftp),'Candidate directory is not empty; no directory removal')
        reply=ftp.rmd(root);need(reply.startswith(('226 ','250 ')),'Empty candidate directory removal did not complete')
    idle();after=verify(protected);need(before==after,'Current deployment hashes differ after maintenance')
    lan.absent(root);vm=args.out/'VM-after';vm.mkdir();values_after=query(lan.HOST,vm)
    need(values_after['boot_before']==values_after['boot_after']==state['current_boot'],'Boot changed after maintenance')
    save(args.out/'result.private.json',dict(completed=True,removed_new_source_files=53,removed_empty_directories=1,
        protected_current_seven_hashes_equal=True,protected_parent_sources=518,protected_required_bundle_inputs=69,
        native_owner_absent=True,VM_after=values_after,recursive_deletion=False,title_launches=0,GPU_calls=0,
        initializer_requests=0,automatic_retries=0))
    print(json.dumps(dict(completed=True,removed_new_source_files=53,current_seven_unchanged=True,GPU_calls=0)))


if __name__=='__main__':main()
