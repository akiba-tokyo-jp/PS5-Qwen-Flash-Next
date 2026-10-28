#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Resolve actual affected translation units before rebuilding a cache variant."""
import argparse,json,os,subprocess
from pathlib import Path
from shader_storage import record
from additional_cache_variant import write_overlay
ROOT=Path(__file__).resolve().parents[1]


def compile_recipes(value,result,alternatives):
    if isinstance(value,list):
        if all(isinstance(x,str)for x in value)and '-c'in value and '-o'in value:
            out=str(Path(value[value.index('-o')+1]).resolve()).casefold()
            previous=result.setdefault(out,value)
            if previous!=value and value not in alternatives.setdefault(out,[]):alternatives[out].append(value)
        else:
            for item in value:compile_recipes(item,result,alternatives)
    elif isinstance(value,dict):
        for item in value.values():compile_recipes(item,result,alternatives)


def inspection_command(command):
    result=[];skip=False
    for token in command:
        if skip:skip=False;continue
        if token in('-o','-MF','-MT','-MQ'):skip=True;continue
        if token in('-c','-MMD','-MD','-MP'):continue
        result.append(token)
    return result+['-H','-fsyntax-only']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('parent','workspace','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prior=json.loads(a.parent.read_text());a.out.mkdir(parents=True)
    rows=list({r['path']:r for r in prior['inputs_before']+[prior['artifact']]}.values())
    for r in rows:
        if record(r['path'])!=r:raise ValueError('Actual cache compilation input changed: '+r['path'])
    recipes={};alternatives={};compile_recipes(prior,recipes,alternatives);read=[]
    for row in rows:
        path=Path(row['path'])
        if path.suffix=='.json'and path.stat().st_size<=16<<20:
            try:value=json.loads(path.read_text())
            except (UnicodeError,json.JSONDecodeError):continue
            compile_recipes(value,recipes,alternatives);read.append(row)
    overlay,changes=write_overlay(rows,a.out/'vfs');changed={str(Path(r['original']).resolve()).casefold()for r in changes}
    linked=[str(Path(x).resolve())for x in prior['link_command']if x.endswith(('.o','.obj'))]
    runtime=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(runtime)+os.pathsep+os.environ.get('PATH',''))
    selected=[];inspected=[];unresolved=[]
    for index,obj in enumerate(linked):
        command=recipes.get(obj.casefold())
        if not command:unresolved.append(obj);continue
        r=subprocess.run(inspection_command(command),cwd=ROOT,capture_output=True,timeout=180,env=env)
        (a.out/f'include-{index}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Existing translation-unit inspection failed: '+r.stderr.decode(errors='replace')[-2500:])
        dependencies=[]
        for line in r.stderr.decode(errors='replace').splitlines():
            if line.startswith('.'):
                _,sep,name=line.partition(' ')
                if sep and Path(name).is_file():dependencies.append(str(Path(name).resolve()))
        source=str(Path(command[command.index('-c')+1]).resolve());dependencies.append(source)
        used=sorted(set(d for d in dependencies if d.casefold()in changed))
        inspected.append(dict(object=obj,affected=bool(used),dependency_count=len(dependencies)))
        if used:selected.append(dict(original_object=obj,command=command,affected_inputs=used,source=record(source),
            historical_command_alternatives=alternatives.get(obj.casefold(),[]),
            selected_recipe_precedence='current native receipt, then captured ancestor order; all new compilation commands are explicit'))
        print(json.dumps(dict(cache_include_inspection=index+1,total=len(linked),affected=len(selected))),flush=True)
    # Objects with no C++ recipe include generated binary/table inputs and native
    # SDK/platform objects. Require that none exposes a cache-geometry symbol.
    nm=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/llvm-nm.exe'
    for i,obj in enumerate(unresolved):
        r=subprocess.run([str(nm),'--demangle',obj],capture_output=True,timeout=60)
        if r.returncode:raise RuntimeError('Unknown cache object cannot be inspected')
        text=r.stdout.decode(errors='replace')
        if any(s in text for s in('PaddedCacheGeometry','selected_padded_cache_slots','selected_padded_cache_geometry','additional_cache_slots')):
            raise ValueError('A geometry consumer has no exact compile recipe: '+obj)
    if not selected:raise ValueError('No actual cache geometry consumer was identified')
    result=dict(schema='ps5-qwen-additional-cache-build-plan-v1',parent=record(a.parent),overlay=record(overlay),
        changes=[dict(original=record(r['original']),replacement=record(r['replacement']))for r in changes],
        selected=selected,inspected=inspected,unresolved_objects_without_geometry_symbols=unresolved,
        native_geometry_qualified=False,PS5_calls=0,CI_runs=0)
    (a.out/'plan.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cache_build_plan_complete=True,affected_translation_units=len(selected),PS5_calls=0)),flush=True)


if __name__=='__main__':main()
