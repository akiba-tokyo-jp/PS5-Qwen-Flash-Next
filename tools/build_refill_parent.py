#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Recompile changed app dependencies and original delivery, then relink."""
import argparse,copy,json,os,re,subprocess
from pathlib import Path
from shader_storage import record
from refill_model_io import generate
from driver_table_storage import audit_linked_storage
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--reuse-app-objects',type=Path,help='Earlier returned app compilations, with unchanged newer-than-dependency objects')
    a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True);(a.out/'tmp').mkdir()
    for row in prior['inputs_before']+[prior['artifact']]:
        if record(row['path'])!=row:raise ValueError('Actual parent input changed: '+row['path'])
    def remap(value):
        return value.replace(str(a.source_root),str(ROOT)).replace(a.source_root.as_posix(),ROOT.as_posix())
    affected={'mapped_source.h','paired_source_io.h'};memo={}
    def depends(path,seen=None):
        path=Path(path).resolve();seen=set()if seen is None else seen
        if path in seen:return False
        if path.name in affected:return True
        if path in memo:return memo[path]
        seen.add(path)
        text=path.read_text(errors='replace')
        for name in re.findall(r'^\s*#\s*include\s*"([^"]+)"',text,re.M):
            for child in (path.parent/name,ROOT/'native/app'/name):
                if child.is_file() and depends(child,seen.copy()):memo[path]=True;return True
        memo[path]=False;return False
    def dependencies(path,seen=None):
        path=Path(path).resolve();seen=set()if seen is None else seen
        if path in seen:return seen
        seen.add(path)
        for name in re.findall(r'^\s*#\s*include\s*"([^"]+)"',path.read_text(errors='replace'),re.M):
            for child in (path.parent/name,ROOT/'native/app'/name):
                if child.is_file():dependencies(child,seen);break
        return seen
    recipes=[];replacements={};origin=[];reused=[]
    for recipe in prior['compile_commands']:
        if '-c'not in recipe:continue
        source=Path(remap(recipe[recipe.index('-c')+1]));old=recipe[recipe.index('-o')+1]
        if old in replacements or not source.is_file():continue
        if source.name not in ('mapped_source.cpp','owned_mapped_backend.cpp')and not depends(source):continue
        if prior['link_command'].count(old)!=1:raise ValueError('Unique linked dependency required: '+old)
        command=[remap(x)for x in recipe];obj=a.out/('app-'+str(len(recipes)+len(reused))+'-'+source.name+'.o')
        command[command.index('-o')+1]=str(obj)
        if a.reuse_app_objects:
            previous=a.reuse_app_objects/obj.name;log=a.reuse_app_objects/(str(len(recipes)+len(reused))+'.private.log')
            deps=dependencies(source)
            if not previous.is_file() or not log.is_file() or any(x.stat().st_mtime_ns>previous.stat().st_mtime_ns for x in deps):
                raise ValueError('Earlier app compilation is absent or older than an actual dependency: '+str(previous))
            reused.append(dict(object=record(previous),source_inputs=[record(x)for x in sorted(deps)],
                completed_compile_log=record(log),compile_command=[str(previous)if x==str(obj)else x for x in command],
                reuse_kind='same unchanged source and dependency tree after the returned later MoE compile error'))
            replacements[old]=str(previous)
        else:replacements[old]=str(obj);recipes.append(command)
        origin.append(dict(original_command=recipe,actual_source=record(source),object_path=str(obj)))
    moe=next(x for x in prior['bounded_model_source_overrides']['objects']if x['source']=='src/llama-moe-cache.cpp')
    recipe=moe['command'].copy();original=Path(recipe[recipe.index('-c')+1])
    generated=a.out/'llama-moe-cache-refill.private.cpp';generated.write_text(generate(original.read_text()),newline='\n')
    obj=a.out/'llama-moe-cache-refill.o';old=moe['object']['path']
    if prior['link_command'].count(old)!=1:raise ValueError('Unique original MoE delivery required')
    command=[remap(x)for x in recipe];command[command.index('-c')+1]=str(generated);command[command.index('-o')+1]=str(obj)
    recipes.append(command);replacements[old]=str(obj)
    image=a.out/'qwen-native.pie.elf';link=[replacements.get(x,x)for x in prior['link_command']]
    link[link.index('-o')+1]=str(image);link=[('-Map='+str(a.out/'native-link.private.map'))if x.startswith('-Map=')else x for x in link]
    frozen=[record(Path(row['path']))for row in prior['inputs_before']]
    for item in reused:frozen += [item['object'],item['completed_compile_log']]+item['source_inputs']
    frozen += [record(x)for x in [Path(__file__),ROOT/'tools/refill_model_io.py',a.parent,original,generated,
        *ROOT.glob('native/app/*.h'),*ROOT.glob('native/app/*.cpp')]]
    env=dict(os.environ,TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'))
    (a.out/'compile-plan.private.json').write_text(json.dumps(dict(frozen_inputs=frozen,commands=recipes+[link],reused=reused),indent=2)+'\n')
    for index,arguments in enumerate(recipes+[link]):
        result=subprocess.run(arguments,cwd=ROOT,capture_output=True,timeout=600,env=env)
        (a.out/(str(index)+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4500:])
        print(json.dumps(dict(completed_compile_or_link=index+1,total=len(recipes)+1)),flush=True)
    for row in frozen:
        if record(row['path'])!=row:raise ValueError('Frozen refill input changed: '+row['path'])
    receipt=copy.deepcopy(prior)
    def current_rows(rows):return [record(remap(row['path']))if remap(row['path'])!=row['path']else row for row in rows]
    receipt['application_sources']=current_rows(prior['application_sources']);receipt['application_headers']=current_rows(prior['application_headers'])
    replacement=next(x for x in receipt['bounded_model_source_overrides']['objects']if x['source']=='src/llama-moe-cache.cpp')
    replacement.update(object=record(obj),command=command,actual_source=record(generated),original_object=moe['object'])
    commands=[]
    for recipe in prior['compile_commands']:
        old=recipe[recipe.index('-o')+1]if '-c'in recipe else None
        if old in replacements:
            commands.append(next(x for x in recipes+[r['compile_command']for r in reused]if x[x.index('-o')+1]==replacements[old]))
        else:commands.append([remap(x)for x in recipe])
    receipt.update(artifact=record(image),link_command=link,compile_commands=commands,source_parent=record(a.parent),
        inputs_before=frozen+[record(x)for x in replacements.values()],
        six_demand_delivery=dict(default_enabled=False,maximum_live_reads=2,additional_workers=0,
            source=record(original),generated=record(generated),rebuilt_app_dependencies=origin,reused_app_compilations=reused,
            original_arithmetic_routing_and_precision_preserved=True),
        lossless_driver_table_geometry=audit_linked_storage(image,prior['lossless_driver_tables']))
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(actual_source_overlay_linked=True,app_dependencies_recompiled=len(origin),PS5_operations=0)),flush=True)
if __name__=='__main__':main()
