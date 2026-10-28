#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Combine the exact 128-slot source owner with coherent phase-priced app objects."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from resident_postload_pricing import SCOPE,entry
import resident_table_admission as tables
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','delivery-parent','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());delivery=json.loads(a.delivery_parent.read_text())
    if prior['post_context_OS_reserve']['selected_post_context_floor_pages']!=962 or not delivery.get('cache128_refill'):
        raise ValueError('Coherent phase-priced app and qualified slot127 delivery source required')
    signature=lambda r:[(x['source'],x['object']['sha256'])for x in r['bounded_model_source_overrides']['objects']]
    if signature(prior)!=signature(delivery)or prior['linked_driver']!=delivery['linked_driver']:
        raise ValueError('The exact original engine, upload and driver objects must match')
    frozen=list({r['path']:r for r in prior['inputs_before']+delivery['inputs_before']+[prior['artifact'],delivery['artifact']]}.values())
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Actual source dependency changed: '+r['path'])
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    main_command=prior['compile_commands'][0].copy()
    folders=[Path(main_command[i+1])for i,x in enumerate(main_command[:-1])if x=='-I']
    for name,transform in(('resident_incremental_tables.h',tables.incremental_header),('resident_direct_tables.h',tables.direct_header)):
        source=next(folder/name for folder in folders if(folder/name).is_file());derived=a.out/name
        derived.write_text(transform(source.read_text()),newline='\n');frozen.extend((record(source),record(derived)))
    template_recipe=delivery['compile_commands'][0];template=Path(template_recipe[template_recipe.index('-c')+1])
    policy=template.parent/'resident_refill_policy.h';private=Path(delivery['cache128_refill']['actual_header']['path'])
    if not policy.is_file():raise ValueError('The actual 128-slot delivery contract is required')
    for source in(policy,private):
        (a.out/source.name).write_bytes(source.read_bytes());frozen.extend((record(source),record(a.out/source.name)))
    phase_command=prior['resident_phase_source']['command'].copy()
    phase_original=Path(delivery['resident_phase_source']['generated_source']['path'])
    phase_source=a.out/'mapped-source-cache128-postload.private.cpp';phase_source.write_bytes(phase_original.read_bytes())
    main_source=a.out/'resident-comparison-cache128-postload.private.cpp';main_source.write_text(tables.entry(entry(template.read_text())),newline='\n')
    commands=[];replacements={};compiled=[]
    for command,source,origin in((phase_command,phase_source,phase_original),(main_command,main_source,template)):
        old=command[command.index('-o')+1];obj=a.out/(source.stem+'.o')
        command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
        command[1:1]=['-I',str(a.out)];command+=['-I',str(origin.parent)]
        if prior['link_command'].count(old)!=1:raise ValueError('Unique exact replaced app object required')
        replacements[old]=str(obj);commands.append(command)
        compiled.append(dict(old=old,source=record(source),object_path=str(obj),command=command))
        frozen.extend((record(source),record(origin)))
    link=[replacements.get(x,x)for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen.extend(record(x)for x in(a.parent,a.delivery_parent,Path(__file__),ROOT/'tools/resident_postload_pricing.py',
        ROOT/'tools/resident_table_admission.py',ROOT/'tools/resident_kernel_min_scope.py',ROOT/'tools/resident_OS_reserve_scope.py'))
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,command in enumerate(commands+[link]):
        result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=600,env=env)
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(cache128_postload_compiled_or_linked=i+1,total=3)),flush=True)
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Fresh cache128 phase-priced input changed')
    receipt=copy.deepcopy(prior)
    receipt.update(artifact=record(image),link_command=link,compile_commands=[main_command],source_parent=record(a.parent),
        delivery_parent=record(a.delivery_parent),inputs_before=frozen+[record(x)for x in replacements.values()],
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    for changed in compiled:
        row=next(x for x in receipt['CPU_metadata_scope']['changed_sources']if x['object_path']==changed['old'])
        row.update(source=changed['source'],object_path=changed['object_path'],command=changed['command'])
    receipt['resident_phase_source'].update(generated_source=record(phase_source),object=record(compiled[0]['object_path']),command=phase_command)
    receipt['resident_context_reuse']['entry']=record(main_source)
    receipt['cache128_refill']=copy.deepcopy(delivery['cache128_refill'])
    receipt['cache128_refill'].update(actual_reader=record(phase_source),actual_header=record(a.out/private.name),native_speed_still_unqualified=True)
    receipt['post_context_OS_reserve'].update(scope=SCOPE,activation_stage='model_loaded_upload_retired_before_context',
        selected_context_entry_pages=1005,selected_post_context_floor_pages=962,native_qualification_pending=True)
    receipt['CPU_table_pricing']=dict(scope=tables.SCOPE,headers=[record(a.out/name)for name in('resident_incremental_tables.h','resident_direct_tables.h')],
        CPU_gate_matches_existing_21_page_scope=True,all_original_hashes_and_readonly_protection_retained=True)
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    if receipt['real_module_import_audit']['missing']:raise ValueError('Native imports missing')
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if not receipt['native_dispatch_audit']['passed']:raise ValueError('Native dispatch failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(cache128_postload_built=True,engine_and_driver_unchanged=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
