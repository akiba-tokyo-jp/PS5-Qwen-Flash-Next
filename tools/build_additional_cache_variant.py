#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compile only the sealed affected units for the isolated 128/134 cache test."""
import argparse,copy,json,os,subprocess
from pathlib import Path
from shader_storage import record
from audit_native_imports import audit
from native_dispatch import audit as dispatch
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def canonical(path):return str(Path(path).resolve()).casefold()


def compile_command(original,obj,dep,overlay):
    result=[];skip=False
    for token in original:
        if skip:skip=False;continue
        if token in('-o','-MF','-MT','-MQ'):skip=True;continue
        if token in('-MMD','-MD','-MP'):continue
        result.append(token)
    return result+['-o',str(obj),'-ivfsoverlay',str(overlay),'-MMD','-MF',str(dep)]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('plan','workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();plan=json.loads(a.plan.read_text())
    if plan['schema']!='ps5-qwen-additional-cache-complete-include-plan-v1' or not plan['all_existing_include_inspections_reused']:
        raise ValueError('Complete actual include selection required')
    if record(plan['parent']['path'])!=plan['parent']or record(plan['overlay']['path'])!=plan['overlay']:
        raise ValueError('Exact selected original native and VFS overlay required')
    prior=json.loads(Path(plan['parent']['path']).read_text());overlay=Path(plan['overlay']['path'])
    frozen=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]+plan['additional_actual_compiler_inputs']}.values())
    frozen +=[record(a.plan),record(Path(__file__)),record(ROOT/'tools/additional_cache_variant.py'),plan['overlay']]
    for row in plan['changes']:frozen.extend((row['original'],row['replacement']))
    for r in frozen:
        if record(r['path'])!=r:raise ValueError('Sealed cache variant source changed: '+r['path'])
    a.out.mkdir(parents=True);(a.out/'tmp').mkdir();commands=[];replacements={};built=[]
    changed={canonical(r['original']['path']):r['replacement']for r in plan['changes']}
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    for i,row in enumerate(plan['selected']):
        obj=a.out/(str(i)+'-'+Path(row['original_object']).name);dep=a.out/(str(i)+'.private.d')
        c=compile_command(row['command'],obj,dep,overlay);commands.append(c)
        replacements[canonical(row['original_object'])]=str(obj)
        (a.out/'planned-commands.private.json').write_text(json.dumps(commands,indent=2)+'\n')
        r=subprocess.run(c,cwd=ROOT,capture_output=True,timeout=600,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
        built.append(dict(original_object=row['original_object'],object=record(obj),command=c,
            logical_source=row['source'],compiled_source=changed.get(canonical(row['source']['path']),row['source']),
            actual_include_inspection=row['include_inspection']))
        print(json.dumps(dict(cache_variant_unit=i+1,total=len(plan['selected']))),flush=True)
    link=[replacements.get(canonical(x),x)if x.endswith(('.o','.obj'))else x for x in prior['link_command']]
    image=a.out/'qwen-native.pie.elf';link[link.index('-o')+1]=str(image)
    link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    r=subprocess.run(link,cwd=ROOT,capture_output=True,timeout=600,env=env);(a.out/'link.private.log').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-5000:])
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen cache variant input changed during compilation')
    by_old={canonical(r['original_object']):r for r in built}
    def updated(row,path_field='object_path',source_field='source'):
        old=row.get(path_field)
        if old and canonical(old)in by_old:
            new=by_old[canonical(old)];row[path_field]=new['object']['path'];row['command']=new['command']
            row['logical_source_before_VFS']=new['logical_source'];row[source_field]=new['compiled_source']
    receipt=copy.deepcopy(prior)
    for row in receipt['CPU_metadata_scope']['changed_sources']:updated(row)
    for row in receipt['bounded_model_source_overrides']['objects']:
        if canonical(row['object']['path'])in by_old:
            new=by_old[canonical(row['object']['path'])];row['object']=new['object'];row['command']=new['command']
            row['actual_source']=new['compiled_source'];row['logical_source_before_VFS']=new['logical_source']
    phase=receipt['resident_phase_source']
    if canonical(phase['object']['path'])in by_old:
        new=by_old[canonical(phase['object']['path'])];phase.update(object=new['object'],command=new['command'],
            generated_source=new['compiled_source'],logical_source_before_VFS=new['logical_source'])
    old_entry=prior['compile_commands'][0][prior['compile_commands'][0].index('-o')+1]
    entry=by_old[canonical(old_entry)]
    receipt.update(artifact=record(image),compile_commands=[entry['command']],link_command=link,
        source_parent=plan['parent'],inputs_before=frozen+[row['object']for row in built],
        additional_cache_geometry=dict(active_slot_candidates=[128,134],plan=record(a.plan),overlay=plan['overlay'],
            compiled=built,commands=commands,actual_entry=entry['compiled_source'],unchanged_driver=True,
            original_files_modified=False,CPU_heap_cap=512<<20,device_cap=1792<<20,single_buffer_cap=512<<20,
            required_new_134_native_layout_qualification=True,model_speed_qualified=False,
            model_requests_per_lifetime=3,six_demand_enabled_in_all_requests=True,only_cache_capacity_varies=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    receipt['post_context_OS_reserve']['original_engine_and_driver_objects_unchanged']=False
    receipt['post_context_OS_reserve']['original_driver_objects_unchanged']=True
    target=a.out/'receipt.private.json';target.write_text(json.dumps(receipt,indent=2)+'\n')
    receipt['real_module_import_audit']=audit(a.workspace,a.cache,a.out)
    receipt['native_dispatch_audit']=dispatch(a.workspace,a.workspace/'driver-work/PS5-Vulkan-Inference-qwen-872cc126',image,a.out/'dispatch')
    if receipt['real_module_import_audit']['missing']or not receipt['native_dispatch_audit']['passed']:raise ValueError('Additional cache import/dispatch audit failed')
    target.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(additional_cache_native_build_complete=True,PS5_calls=0)),flush=True)


if __name__=='__main__':main()
