#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile the exact recovered cache and compare its actual retained object."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from build_performance_quantizer import record
from driver_table_storage import sections
from start_success_route import load,need,save
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','source-proof','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--resume',action='store_true',help='Continue only an incomplete host compilation after restoring a missing generated include')
    a=p.parse_args();proof=load(a.source_proof);need(proof['completed'] and proof['source_bytes_exact'] and
        record(proof['source']['path'])==proof['source'],'The complete selected source bytes must already be exact')
    native=load(a.current/'provenance/native-link.receipt.private.json');retained=load(a.current/'provenance/retained-relink-inputs.private.json')
    command=native['routing_sharing']['commands'][1].copy();old_source=command[command.index('-c')+1];old_object=command[command.index('-o')+1]
    rows=[r for r in retained if r['original_path']==old_object];need(len(rows)==1,'One selected actual cache provider required')
    original={k:rows[0][k] for k in ('path','bytes','sha256')};need(record(original['path'])==original,'The actual selected cache object changed')
    a.out.mkdir(parents=True,exist_ok=a.resume)
    need(not(a.out/'result.private.json').exists(),'A completed cache compilation is never replayed')
    selected=load(a.current/'provenance/selected-entry-build.private.json');profile=load(selected['application_policy']['path'])
    directory=Path(profile['source']['path']).parent
    for path in directory.glob('*.h'):shutil.copyfile(path,a.out/path.name)
    # The original policy builder copies this maintained header byte-for-byte
    # under a unique include name. Restore that exact generated alias.
    shutil.copyfile(ROOT/'native/app/expert_policy.h',a.out/'candidate_expert_policy.h')
    # The original additional-cache VFS also admitted the134-slot historical
    # geometry. Keep that exact default-off branch in the retained cache.
    from additional_cache_variant import transform
    reset=ROOT/'native/app/resident_cache_reset.h'
    (a.out/reset.name).write_text(transform(reset,reset.read_text()),newline='\n')
    selected_command=next(c for c in selected['commands'] if '-ivfsoverlay' in c)
    view=load(selected_command[selected_command.index('-ivfsoverlay')+1])
    for row in view['roots']:
        path=a.out/Path(row['external-contents']).name
        if path.exists():row['external-contents']=path.resolve().as_posix()
    overlay=a.out/'selected-view.private.json'
    if overlay.exists():need(a.resume and load(overlay)==view,'The recovered selected header view changed')
    else:save(overlay,view)
    source=a.out/'cache.private.cpp';source.write_text('#line 1 '+json.dumps(old_source)+'\n'+Path(proof['source']['path']).read_text(),newline='\n')
    obj=a.out/'cache.o';command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    if '-MF' in command:command[command.index('-MF')+1]=str(a.out/'cache.private.d')
    new=[];index=0
    while index<len(command):
        if command[index]=='-ivfsoverlay':index+=2;continue
        new.append(command[index]);index+=1
    command=new;command[1:1]=['-I',str(a.out),'-ivfsoverlay',str(overlay)]
    run=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
    (a.out/'compile.private.log').write_bytes(run.stdout+run.stderr)
    need(not run.returncode,(run.stdout+run.stderr).decode(errors='replace')[-4000:])
    old,new=sections(Path(original['path']).read_bytes()),sections(obj.read_bytes());differences=[]
    if len(old)!=len(new):differences.append('section_count')
    else:
        for left,right in zip(old,new):
            if any(left[k]!=right[k] for k in ('name','type','flags','bytes','info','alignment','data')):differences.append(left['name'])
    exact=record(obj)['sha256']==original['sha256']
    save(a.out/'result.private.json',dict(completed=True,source_proof=record(a.source_proof),source=record(source),
        artifact=record(obj),actual_provider=original,command=command,selected_VFS_view=record(overlay),
        selected_object_byte_exact=exact,section_differences=differences,PS5_operations=0,model_tests_replayed=0,
        baseline_provider_qualified=exact and not differences))
    print(dict(completed=True,selected_object_byte_exact=exact,section_differences=differences,PS5_operations=0))


if __name__=='__main__':main()
