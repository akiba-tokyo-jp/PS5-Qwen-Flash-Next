#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check bounded ready-expert graphs and actual-model router observation sources."""
import argparse,json,os,re,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def check_ready_only(a,up,host,library):
    """Check changed ready graphs without rebuilding the unchanged model/router."""
    source=a.out/'ready-control-native.cpp'
    source.write_text('#include "ready_expert_graph.h"\n'
        'ggml_cgraph *serial_ready(ggml_context*c,const std::array<qwen_app::ReadyExpertGraphInputs,2>&g,ggml_tensor*o)'
        '{return qwen_app::build_serial_ready_expert_graph(c,g,o);}\n',newline='\n')
    prior_path=a.cache/'build/application-native-acceleration-2830/receipt.private.json';prior=json.loads(prior_path.read_text())
    native=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    native[native.index('-c')+1]=str(source);native[native.index('-o')+1]=str(a.out/'ready-control-PS5.o')
    native+=['-Wall','-Wextra','-Werror']
    for i in range(len(native)-1):
        if native[i]=='-I'and Path(native[i+1]).is_relative_to(up):native[i]='-isystem'
    test=ROOT/'tests/ready_expert_graph.cpp';exe=a.out/'ready-control.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),str(test),str(library),'-o',str(exe)],[str(exe)],native]
    files=[Path(__file__),test,source,library,prior_path,*[ROOT/'native/app'/n for n in
        ('ready_expert_graph.h','split_padded_bank.h','padded_bank.h','padded_bank_layout.h')]]
    fixed=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=180,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Ready control '+str(i)+': '+r.stderr.decode(errors='replace')[-3000:])
        if i==1:controls=json.loads(r.stdout)
    assert controls['serial_control_graphs']==9 and controls['actual_GGML_partial_expert_graphs']==20
    assert controls['original_order_F32_reduction_values']==2560
    assert fixed==[record(f)for f in files]
    result=dict(inputs=fixed,commands=commands,controls=controls,actual_native_SDK_compiled=True,
        changed_ready_graphs_only=True,model_router_rebuilt=False,native_GPU_arithmetic_qualified=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(controls),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--ready-only',action='store_true',help='Check changed ready controls without rebuilding unchanged router/model units')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    providers=list((a.cache/'host-CPU-reference-066/build').rglob('ggml-base.a'))+list((a.cache/'host-CPU-reference-066/build').rglob('libggml-base.a'))
    if len(providers)!=1:raise ValueError('Exact existing GGML provider required')
    library=providers[0]
    if a.ready_only:return check_ready_only(a,up,host,library)
    files=[Path(__file__),library,up/'ggml/include/ggml.h',up/'ggml/include/ggml-backend.h']
    files += [ROOT/name for name in('native/app/ready_expert_graph.h','native/app/split_padded_bank.h','native/app/padded_bank.h',
        'native/app/router_shadow_graph.h','native/app/router_shadow_callback.h','native/app/router_shadow_observer.h',
        'tests/ready_expert_graph.cpp','tests/router_shadow_observer.cpp','patches/experimental-router-shadow/0001-bounded-router-shadow.patch')]
    model=up/'src/models/qwen4exp.cpp';recipes_path=a.cache/'build/llama-ps5/compile_commands.json'
    recipes=json.loads(recipes_path.read_text());matching=[]
    for recipe in recipes:
        unity=Path(recipe['file'])
        if 'Unity'in unity.parts and model.as_posix()in unity.read_text():matching.append(recipe)
    if len(matching)!=1:raise ValueError('Exact model unity recipe required')
    recipe=matching[0];original_unity=Path(recipe['file']);text=original_unity.read_text()
    files += [model,recipes_path,original_unity]+[Path(s)for s in re.findall(r'^#include "([^"]+)"',text,re.M)]
    isolated=a.out/'isolated';target=isolated/'src/models/qwen4exp.cpp';target.parent.mkdir(parents=True)
    target.write_bytes(model.read_bytes().replace(b'\r\n',b'\n'))
    patch=ROOT/'patches/experimental-router-shadow/0001-bounded-router-shadow.patch'
    r=subprocess.run(['git','apply',str(patch.resolve())],cwd=isolated,capture_output=True,timeout=30)
    (a.out/'patch.private.log').write_bytes(r.stdout+r.stderr)
    if r.returncode:raise RuntimeError('Isolated router observation patch failed')
    unity=a.out/'router-shadow-model-unity.cxx';unity.write_text(text.replace(model.as_posix(),target.resolve().as_posix()),newline='\n')
    native_source=a.out/'remaining-graph-native.cpp'
    native_source.write_text('#include "ready_expert_graph.h"\n#include "router_shadow_graph.h"\n#include "router_shadow_callback.h"\n'
        'ggml_cgraph *ready_graph(ggml_context*c,const qwen_app::ReadyExpertGraphInputs&a){return qwen_app::build_ready_expert_graph(c,a);}\n'
        'ggml_cgraph *ready_sum(ggml_context*c,ggml_tensor*a,ggml_tensor*b){return qwen_app::build_ready_expert_reduction(c,a,b);}\n'
        'ggml_cgraph *ready_serial(ggml_context*c,const std::array<qwen_app::ReadyExpertGraphInputs,2>&g,ggml_tensor*o){return qwen_app::build_serial_ready_expert_graph(c,g,o);}\n'
        'ggml_tensor *shadow_graph(ggml_context*c,ggml_tensor*a,ggml_tensor*b){return qwen_app::build_router_shadow(c,a,b);}\n'
        'bool shadow_callback(ggml_tensor*t,bool ask,void*p){return qwen_app::RouterShadowCallback::evaluate(t,ask,p);}\n',newline='\n')
    prior_path=a.cache/'build/application-native-PLE-2654/receipt.private.json';prior=json.loads(prior_path.read_text())
    native=next(c.copy()for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name=='llama_engine.cpp')
    native[native.index('-c')+1]=str(native_source);native[native.index('-o')+1]=str(a.out/'remaining-graph-native.o')
    native+=['-Wall','-Wextra','-Werror']
    files += [target,unity,native_source,prior_path];fixed=[record(f)for f in files]
    commands=[];executions={}
    common=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include')]
    for name in('ready_expert_graph','router_shadow_observer'):
        exe=a.out/(name+'.exe');commands += [common+[str(ROOT/'tests'/(name+'.cpp')),str(library),'-o',str(exe)],[str(exe)]]
        executions[len(commands)-1]=name
    commands.append(native)
    for layer in(None,23):
        command=recipe['command'];old=str(original_unity.resolve())
        if command.count(old)!=1:raise ValueError('Unique original unity source required')
        command=command.replace(old,subprocess.list2cmdline([str(unity.resolve())]))
        command,count=re.subn(r'(?<=\s)-o\s+(?:"[^"]+"|\S+)',lambda _:'-o '+subprocess.list2cmdline([str((a.out/f'router-shadow-{layer}.o').resolve())]),command)
        if count!=1:raise ValueError('Unique native output required')
        command+=' -I'+subprocess.list2cmdline([str(ROOT/'native/app')])+' -I'+subprocess.list2cmdline([str(model.parent)])
        if layer is not None:command+=' -DQWEN_EXPERIMENTAL_ROUTER_SHADOW_LAYER='+str(layer)
        commands.append(command)
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls={}
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=180,env=env,cwd=recipe['directory']if isinstance(c,str)else None)
        (a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Remaining graph '+str(i)+': '+r.stderr.decode(errors='replace')[-3000:])
        if i in executions:controls[executions[i]]=json.loads(r.stdout)
        print('Graph check '+str(i)+' passed',flush=True)
    assert controls['ready_expert_graph']['actual_GGML_partial_expert_graphs']==20
    assert controls['ready_expert_graph']['original_order_F32_reduction_values']==2560
    assert controls['router_shadow_observer']['bounded_complete_records']==384
    assert fixed==[record(f)for f in files]
    result=dict(inputs=fixed,commands=commands,controls=controls,actual_SDK_compile_passed=True,
        actual_model_shadow_off_and_layer23_compiled=True,native_model_link_or_execution=False,
        native_GPU_placement_or_arithmetic_qualified=False,production_sources_or_driver_changed=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(controls),flush=True)
if __name__=='__main__':main()
