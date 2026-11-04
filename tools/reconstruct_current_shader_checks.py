#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recover both selected shader CPU checks and reproduce their complete objects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from additional_shader_source import transform as asset_source
from build_performance_quantizer import record
from driver_table_storage import sections
from resident_shader_integrity import session_source
from start_success_route import load,need,save

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('current','base-entry','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();native=load(a.current/'provenance/native-link.receipt.private.json')
    retained=load(a.current/'provenance/retained-relink-inputs.private.json');base=load(a.base_entry);profile=load(base['application_policy']['path'])
    a.out.mkdir(parents=True,exist_ok=False)
    for header in Path(profile['source']['path']).parent.glob('*.h'):shutil.copyfile(header,a.out/header.name)
    overlay=load(base['commands'][1][base['commands'][1].index('-ivfsoverlay')+1])
    for root in overlay['roots']:root['external-contents']=(a.out/Path(root['external-contents']).name).resolve().as_posix()
    view=a.out/'selected-view.private.json';save(view,overlay)
    outputs={}
    for name,filename,transform in [('budget5.o','shader_assets.cpp',asset_source),('budget6.o','shader_file_session.cpp',session_source)]:
        row=next(r for r in native['CPU_metadata_scope']['changed_sources'] if Path(r['object_path']).name==name)
        provider=next(r for r in retained if r['original_path']==row['object_path'])
        need(record(provider['path'])=={k:provider[k] for k in ('path','bytes','sha256')},'Selected shader check changed')
        original=ROOT/'native/app'/filename;text=transform(original.read_text(encoding='utf-8'));raw=text.encode()
        need(len(raw)==row['source']['bytes'] and hashlib.sha256(raw).hexdigest()==row['source']['sha256'],
             'The complete original shader check source did not reproduce')
        command=row['command'].copy();original_path=command[command.index('-c')+1]
        source=a.out/(Path(original_path).name);source.write_text('#line 1 '+json.dumps(original_path)+'\n'+text,encoding='utf-8',newline='\n')
        filtered=[];i=0
        while i<len(command):
            if command[i]=='-ivfsoverlay':i+=2;continue
            filtered.append(command[i]);i+=1
        command=filtered;command[1:1]=['-I',str(a.out),'-I',str(ROOT/'native/app'),'-ivfsoverlay',str(view)]
        obj=a.out/name;command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        if '-MF'in command:command[command.index('-MF')+1]=str(a.out/(name+'.private.d'))
        result=subprocess.run(command,capture_output=True,timeout=240,env=dict(os.environ,TMP=str(a.out),TEMP=str(a.out)))
        (a.out/(name+'.compile.private.log')).write_bytes(result.stdout+result.stderr)
        need(result.returncode==0,result.stderr.decode(errors='replace')[-3500:])
        old,new=sections(Path(provider['path']).read_bytes()),sections(obj.read_bytes())
        differences=['section_count'] if len(old)!=len(new) else [l['name'] for l,r in zip(old,new)
            if any(l[k]!=r[k] for k in ('name','type','flags','bytes','info','alignment','data'))]
        exact=record(obj)['sha256']==provider['sha256']
        outputs[name]=dict(source=record(source),artifact=record(obj),actual_provider={k:provider[k] for k in ('path','bytes','sha256')},
            command=command,selected_object_byte_exact=exact,section_differences=differences,original_source_SHA256=row['source']['sha256'])
        print(json.dumps(dict(provider=name,complete_source_reproduced=True,selected_object_byte_exact=exact,section_differences=differences)),flush=True)
    save(a.out/'result.private.json',dict(completed=True,providers=outputs,all_selected_objects_byte_exact=all(r['selected_object_byte_exact'] for r in outputs.values()),
        inputs=[record(ROOT/'tools/additional_shader_source.py'),record(ROOT/'tools/resident_shader_integrity.py'),
            record(ROOT/'native/app/shader_assets.cpp'),record(ROOT/'native/app/shader_file_session.cpp')],PS5_operations=0,production_adopted=False))


if __name__=='__main__':main()
