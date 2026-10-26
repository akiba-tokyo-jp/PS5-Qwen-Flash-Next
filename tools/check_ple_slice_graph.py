#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check PLE copy elision using actual GGML metadata and deterministic address fixtures."""
import argparse,json,os,re,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    providers=list((a.cache/'host-CPU-reference-066/build').rglob('ggml-base.a'))+list((a.cache/'host-CPU-reference-066/build').rglob('libggml-base.a'))
    if len(providers)!=1:raise ValueError('Exact existing metadata provider required')
    library=providers[0];files=[Path(__file__),library,up/'ggml/include/ggml.h',ROOT/'native/app/ple_slice_graph.h',ROOT/'tests/ple_slice_graph.cpp']
    for name in('ggml-vulkan.cpp','vulkan-shaders/generic_binary_head.glsl','vulkan-shaders/mul.comp'):
        files.append(up/'ggml/src/ggml-vulkan'/name)
    patch=ROOT/'patches/experimental-ple/0001-bounded-tap-views.patch'
    model=up/'src/models/qwen4exp.cpp';recipes_path=a.cache/'build/llama-ps5/compile_commands.json'
    recipes=json.loads(recipes_path.read_text());matching=[]
    for recipe in recipes:
        unity=Path(recipe['file'])
        if 'Unity'in unity.parts and model.as_posix()in unity.read_text():matching.append(recipe)
    if len(matching)!=1:raise ValueError('Exact original model unity compile recipe required')
    recipe=matching[0];original_unity=Path(recipe['file']);unity_text=original_unity.read_text()
    includes=[Path(s)for s in re.findall(r'^#include "([^"]+)"',unity_text,re.M)]
    if includes.count(model)!=1:raise ValueError('One original model in native unity required')
    files.extend((patch,recipes_path,original_unity,*includes))
    isolated=a.out/'isolated';target=isolated/'src/models/qwen4exp.cpp';target.parent.mkdir(parents=True,exist_ok=False)
    target.write_bytes(model.read_bytes().replace(b'\r\n',b'\n'))
    patch_command=['git','apply',str(patch.resolve())]
    applied=subprocess.run(patch_command,cwd=isolated,capture_output=True,timeout=30)
    (a.out/'patch.private.log').write_bytes(applied.stdout+applied.stderr)
    if applied.returncode:raise RuntimeError('Isolated PLE patch failed')
    unity=a.out/'ple-model-unity.cxx'
    unity.write_text(unity_text.replace(model.as_posix(),target.resolve().as_posix()),newline='\n')
    files.extend((target,unity))
    native_source=a.out/'ple-slice-native.cpp'
    native_source.write_text('#include "ple_slice_graph.h"\nqwen_app::PLETaps instantiate(ggml_context*c,ggml_tensor*p,ggml_tensor*k)'
        '{return qwen_app::build_experimental_PLE_tap(c,p,k,4,3,qwen_app::PLESliceMode::both_copies_elided);}\n',newline='\n')
    prior_path=a.cache/'build/application-native-metadata-2615/receipt.private.json';prior=json.loads(prior_path.read_text())
    native=next(c.copy()for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    native[native.index('-c')+1]=str(native_source);native[native.index('-o')+1]=str(a.out/'ple-slice-native.o')
    native+=['-Wall','-Wextra','-Werror'];files.extend((native_source,prior_path));fixed=[record(f)for f in files]
    exe=a.out/'ple-slices.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),str(ROOT/'tests/ple_slice_graph.cpp'),str(library),'-o',str(exe)],
        [str(exe)],native]
    for mode in range(4):
        command=recipe['command'];old=str(original_unity.resolve())
        if command.count(old)!=1:raise ValueError('Original unity source argument is not unique')
        command=command.replace(old,subprocess.list2cmdline([str(unity.resolve())]))
        command,count=re.subn(r'(?<=\s)-o\s+(?:"[^"]+"|\S+)',lambda _:'-o '+subprocess.list2cmdline([str((a.out/f'ple-model-{mode}.o').resolve())]),command)
        if count!=1:raise ValueError('Native output argument is not unique')
        command+=' -I'+subprocess.list2cmdline([str(ROOT/'native/app')])
        command+=' -I'+subprocess.list2cmdline([str(model.parent)])+' -DQWEN_EXPERIMENTAL_PLE_SLICE_MODE='+str(mode)
        commands.append(command)
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env,cwd=recipe['directory']if isinstance(c,str)else None);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('PLE graph '+str(i)+': '+r.stderr.decode(errors='replace')[-2500:])
        if i==1:controls=json.loads(r.stdout)
        if i>=3:print('Native model mode '+str(i-3)+' compiled',flush=True)
    assert controls['actual_GGML_tap_graphs']==64 and controls['exact_F32_values']==1638400
    assert fixed==[record(f)for f in files]
    result=dict(controls=controls,inputs=fixed,commands=commands,actual_SDK_header_compilation=True,
        isolated_actual_model_unit_modes_compiled=[0,1,2,3],maintained_production_sources_changed=False,
        actual_backend_arithmetic_or_speed_qualified=False,model_graph_runtime_integration=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('inputs','commands')}),flush=True)
if __name__=='__main__':main()
