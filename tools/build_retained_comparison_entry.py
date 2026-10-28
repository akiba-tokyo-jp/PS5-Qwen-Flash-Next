#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the complete CPU-stage app view and replace only a comparison entry."""
import argparse
import copy
import json
import os
import subprocess
from pathlib import Path
from audit_native_imports import audit
from driver_table_storage import audit_linked_storage
from native_dispatch import audit as dispatch
from resident_context_entry import generate
from shader_storage import record

ROOT=Path(__file__).resolve().parents[1]


def main_recipe(receipt):
    rows=[c for c in receipt['compile_commands'] if '-c' in c and
          'resident-comparison' in Path(c[c.index('-c')+1]).name]
    if len(rows)!=1:
        raise ValueError('One actual resident comparison entry recipe required')
    return rows[0]


def apply_qualified_CPU_entry(text, qualified):
    needle='        qwen_app_configure_resident_cache_reuse(true);'
    start=qualified.index('        const Json CPU_scope=')
    end=qualified.index('        qwen_app_select_resident_CPU_metadata_scope(true);',start)
    end=qualified.index('\n',end)+1
    if text.count(needle)!=1:
        raise ValueError('One retained-context activation required')
    text=text.replace(needle,needle+'\n'+qualified[start:end])
    needle='        resident_sample("phase_local_after_startup_settle");'
    end_scope='''
        qwen_app_select_resident_CPU_metadata_scope(false);
        if(qwen_app_resident_CPU_metadata_scope_active())throw std::runtime_error("CPU scope must end before original GPU admission");'''
    if text.count(needle)!=1 or needle+end_scope not in qualified:
        raise ValueError('Qualified once-only CPU-to-GPU boundary required')
    text=text.replace(needle,needle+end_scope)
    needle='\n        qwen_native_gpu_initialize((startup.admission_report+".driver.log").c_str());'
    guard='\n        if(qwen_app_resident_CPU_metadata_scope_active())throw std::runtime_error("GPU initialization cannot use the CPU metadata floor");'
    if text.count(needle)!=1 or guard+needle not in qualified:
        raise ValueError('Qualified unchanged GPU entry guard required')
    text=text.replace(needle,guard+needle)
    text=text.replace('{"kernel_extra_margin_bytes",qwen_app::kernel_memory_margin}',
        '{"kernel_extra_margin_bytes",qwen_app_resident_CPU_metadata_scope_active()?21ull*16384:qwen_app::kernel_memory_margin},{"CPU_metadata_scope_active",qwen_app_resident_CPU_metadata_scope_active()}')
    return text


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent','entry-parent','workspace','cache','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());entry=json.loads(a.entry_parent.read_text())
    if not (prior['CPU_metadata_scope']['GPU_operational_floor_unchanged'] and
            prior['resident_context_reuse']['metadata_only_reset']):
        raise ValueError('Complete retained-context CPU-stage parent required')
    for row in prior['inputs_before']+entry['inputs_before']+[prior['artifact'],entry['artifact']]:
        if record(row['path'])!=row:
            raise ValueError('Immutable comparison input changed: '+row['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    parent_recipe=main_recipe(prior);template_recipe=main_recipe(entry)
    qualified=Path(parent_recipe[parent_recipe.index('-c')+1]);template=Path(template_recipe[template_recipe.index('-c')+1])
    source=a.out/'resident-comparison-retained-CPU.private.cpp'
    source.write_text(apply_qualified_CPU_entry(generate(template.read_text()),qualified.read_text()),newline='\n')
    obj=a.out/'resident-comparison-retained-CPU.o';command=parent_recipe.copy()
    old_object=command[command.index('-o')+1]
    command[command.index('-c')+1]=str(source);command[command.index('-o')+1]=str(obj)
    command+=['-I',str(qualified.parent),'-I',str(template.parent)]
    if prior['link_command'].count(old_object)!=1:
        raise ValueError('Unique actually linked original entry required')
    link=[str(obj) if x==old_object else x for x in prior['link_command']]
    image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen=prior['inputs_before']+entry['inputs_before']+[record(x)for x in
        (Path(__file__),ROOT/'tools/resident_context_entry.py',a.parent,a.entry_parent,qualified,template,source)]
    for i,recipe in enumerate((command,link)):
        result=subprocess.run(recipe,cwd=ROOT,capture_output=True,timeout=600,
            env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp')))
        (a.out/f'{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors='replace')[-4500:])
    for row in frozen:
        if record(row['path'])!=row:
            raise ValueError('Frozen comparison input changed')
    receipt=copy.deepcopy(prior)
    receipt.update(artifact=record(image),link_command=link,compile_commands=[command],
        source_parent=record(a.parent),entry_parent=record(a.entry_parent),inputs_before=frozen+[record(obj)],
        retained_entry_replacement=dict(original=record(template),generated=record(source),
            original_complete_CPU_stage_app_objects_retained=True,only_entry_recompiled=True,
            model_and_driver_objects_unchanged=True,GPU_floor_unchanged=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['resident_context_reuse']['entry']=record(source)
    path=a.out/'receipt.private.json';path.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    if receipt['real_module_import_audit']['missing']:
        raise ValueError('Actual native imports missing')
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if not receipt['native_dispatch_audit']['passed']:
        raise ValueError('Native dispatch audit failed')
    path.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(retained_entry_linked=True,only_entry_recompiled=True,PS5_operations=0)),flush=True)


if __name__=='__main__':main()
