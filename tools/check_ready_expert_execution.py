#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check the actual ready execution and compile its real PS5 graph adapter."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('one-graph','split-serial','split-overlap','repeat','first-exception','second-exception',
    'missing-role','false-0','false-1','false-2','throw-0','throw-1','throw-2','wrong-thread',
    'invalid-mode','wrong-prior','expired','serial-partial-ready','serial-stale-completion','serial-wrong-completion')
ADAPTER_SCENARIOS=('one-graph','split-overlap','before-allocation','early-close','repeat-close','CPU-backend',
    'oversized-plan','allocation-failed','oversized-buffer','device-ledger','Flexible-reserve','Direct-reserve',
    'wrong-mask','wrong-epoch','wrong-order','compute-failed','sync-failed','checkpoint-failed','stage-failed','dispatch-memory')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in('workspace','cache','qualified-native','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    test=ROOT/'tests/ready_expert_execution.cpp';native_source=ROOT/'native/app/ready_expert_native.cpp'
    exe=a.out/'ready-execution.exe'
    host_cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(test),'-o',str(exe)]
    prior=json.loads(a.qualified_native.read_text())
    original=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    native=[]
    for src in(test,native_source):
        c=original.copy();c[c.index('-c')+1]=str(src);c[c.index('-o')+1]=str(a.out/(src.stem+'-PS5.o'))
        c+=['-Wall','-Wextra','-Werror'];native.append(c)
    up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    libraries=list((a.cache/'host-CPU-reference-066/build').rglob('libggml-base.a'))+list((a.cache/'host-CPU-reference-066/build').rglob('ggml-base.a'))
    if len(libraries)!=1:raise ValueError('One exact existing GGML metadata provider required')
    system_paths=[Path(original[i+1])for i,v in enumerate(original[:-1])if v=='-isystem']
    kernel=next(p/'ps5platform/kernel.h'for p in system_paths if(p/'ps5platform/kernel.h').is_file())
    header=a.out/'include/ps5platform/kernel.h';header.parent.mkdir(parents=True);shutil.copyfile(kernel,header)
    adapter_test=ROOT/'tests/ready_expert_native.cpp';adapter_exe=a.out/'ready-native.exe'
    adapter_cmd=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
        '-I',str(up/'ggml/include'),'-I',str(a.out/'include')]
    # Rename only the test translation units' device API seams. Keep the real
    # metadata archive immutable and never route its fake backend into a real
    # graph-compute implementation. Native SDK compilation uses no such macros.
    adapter_cmd+=['-D'+name+'=qwen_test_'+name for name in('ggml_backend_is_vk',
        'ggml_backend_get_default_buffer_type','ggml_backend_alloc_ctx_tensors_from_buft_size',
        'ggml_backend_alloc_ctx_tensors','ggml_backend_buffer_get_size','ggml_backend_buffer_free',
        'ggml_backend_graph_compute','ggml_backend_synchronize')]
    adapter_cmd+=[str(adapter_test),str(native_source),str(libraries[0]),'-o',str(adapter_exe)]
    files=[Path(__file__),test,ROOT/'tests/ready_source_coordinator.cpp',a.qualified_native,native_source,
        *[ROOT/'native/app'/n for n in('ready_expert_native.h','ready_expert_graph.h','ready_expert_execution.h',
        'ready_source_coordinator.h','ready_expert_wave.h','vectored_source_batch.h','split_padded_bank.h','padded_bank.h',
        'device_buffer_budget.h','native_gpu.h','system_memory.h')],adapter_test,kernel,header,libraries[0],
        *[up/'ggml/include'/n for n in('ggml.h','ggml-backend.h','ggml-alloc.h','ggml-vulkan.h')]]
    inputs=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));results=[]
    commands=[host_cmd,*[[str(exe),s]for s in SCENARIOS],*native,adapter_cmd,*[[str(adapter_exe),s]for s in ADAPTER_SCENARIOS]]
    adapter_results=[]
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=60,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Ready execution '+str(i)+': '+(r.stdout+r.stderr).decode(errors='replace')[-3000:])
        if 1<=i<=len(SCENARIOS):
            v=json.loads(r.stdout);assert v['passed']and v['PS5_operations']==v['GPU_calls']==v['file_reads']==0
            results.append(dict(scenario=SCENARIOS[i-1],**v))
        elif i>=len(commands)-len(ADAPTER_SCENARIOS):
            v=json.loads(r.stdout);assert v['passed']and v['PS5_operations']==v['GPU_calls']==v['physical_weight_bytes']==0
            adapter_results.append(dict(scenario=ADAPTER_SCENARIOS[i-(len(commands)-len(ADAPTER_SCENARIOS))],**v))
    assert [v['graph_completion_callbacks']for v in results[:3]]==[1,3,3]
    assert [v['callbacks_during_GPU_lease']for v in results[:3]]==[0,0,15]
    assert inputs==[record(f)for f in files]
    receipt=dict(schema='ps5-qwen-ready-execution-host-v1',inputs=inputs,commands=commands,controls=results,adapter_controls=adapter_results,
        native_SDK_objects=[record(a.out/(src.stem+'-PS5.o'))for src in(test,native_source)],
        actual_application_state_machines_exercised=True,physical_GPU_or_numerical_validation=False,
        native_fixture_entry_and_model_integration_complete=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(scenarios=len(results),native_adapter_scenarios=len(adapter_results),native_SDK_compiled=True,physical_GPU_qualified=False,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
