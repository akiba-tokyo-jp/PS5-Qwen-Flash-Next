#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse all coherent kernel-margin app objects and replace only a native entry."""
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
    for name in ('parent','entry-parent','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--CPU-tables-only',action='store_true')
    a=p.parse_args();prior=json.loads(a.parent.read_text());template=json.loads(a.entry_parent.read_text())
    if not a.CPU_tables_only and prior['post_context_OS_reserve']['selected_post_context_floor_pages']!=962:
        raise ValueError('Complete coherent minimum-plus-metadata app objects required')
    def signature(r):return [(x['source'],x['object']['sha256'])for x in r['bounded_model_source_overrides']['objects']]
    if signature(prior)!=signature(template)or prior['linked_driver']!=template['linked_driver']:
        raise ValueError('Original engine/delivery/driver objects must match before entry reuse')
    frozen=list({row['path']:row for row in prior['inputs_before']+template['inputs_before']+[prior['artifact'],template['artifact']]}.values())
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Exact reused native input changed: '+row['path'])
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir()
    command=prior['compile_commands'][0].copy();original_recipe=template['compile_commands'][0]
    original=Path(original_recipe[original_recipe.index('-c')+1])
    source=a.out/'resident-comparison-postload.private.cpp'
    transformed=original.read_text()if a.CPU_tables_only else entry(original.read_text())
    source.write_text(tables.entry(transformed),newline='\n')
    include_folders=[Path(command[i+1])for i,x in enumerate(command[:-1])if x=='-I']
    for name,transform in (('resident_incremental_tables.h',tables.incremental_header),('resident_direct_tables.h',tables.direct_header)):
        origin=next(folder/name for folder in include_folders if (folder/name).is_file())
        derived=a.out/name;derived.write_text(transform(origin.read_text()),newline='\n')
        frozen.extend((record(origin),record(derived)))
    old=command[command.index('-o')+1];obj=a.out/'resident-comparison-postload.o'
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    command[1:1]=['-I',str(a.out)];command+=['-I',str(original.parent)]
    if prior['link_command'].count(old)!=1:raise ValueError('One actual linked native entry required')
    link=[str(obj)if x==old else x for x in prior['link_command']];image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen+=[record(x)for x in(a.parent,a.entry_parent,Path(__file__),ROOT/'tools/resident_postload_pricing.py',
        ROOT/'tools/resident_kernel_min_scope.py',ROOT/'tools/resident_OS_reserve_scope.py',ROOT/'tools/resident_table_admission.py',original,source)]
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,recipe in enumerate((command,link)):
        result=subprocess.run(recipe,cwd=ROOT,capture_output=True,timeout=600,env=env)
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-5000:])
        print(json.dumps(dict(postload_entry_compiled_or_linked=i+1,total=2)),flush=True)
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Fresh postload input changed')
    receipt=copy.deepcopy(prior);receipt.update(artifact=record(image),link_command=link,compile_commands=[command],
        source_parent=record(a.parent),entry_parent=record(a.entry_parent),inputs_before=frozen+[record(obj)],
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    selected=next(row for row in receipt['CPU_metadata_scope']['changed_sources']if row['object_path']==old)
    selected.update(source=record(source),object_path=str(obj),command=command)
    receipt['resident_context_reuse']['entry']=record(source)
    if not a.CPU_tables_only:
        receipt['post_context_OS_reserve'].update(scope=SCOPE,activation_stage='model_loaded_upload_retired_before_context',
            selected_context_entry_pages=1005,selected_post_context_floor_pages=962,only_entry_recompiled=True,
            original_GPU_initialization_and_model_load_floors_unchanged=True,native_qualification_pending=True)
    receipt['CPU_table_pricing']=dict(scope=tables.SCOPE,headers=[record(a.out/name)for name in('resident_incremental_tables.h','resident_direct_tables.h')],
        CPU_gate_matches_existing_21_page_scope=True,all_original_hashes_and_readonly_protection_retained=True)
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    if receipt['real_module_import_audit']['missing']:raise ValueError('Native imports missing')
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if not receipt['native_dispatch_audit']['passed']:raise ValueError('Native dispatch failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(postload_entry_built=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
