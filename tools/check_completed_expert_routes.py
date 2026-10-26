#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check completed-ID observation with real GGML CPU I/O and the PS5 ABI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('positive','width3','width4','internal_sync','other_thread_sync','other_backend_sync',
 'get_failure','sync_failure','negative_id','large_id','bad_layer','wrong_order','width8','bad_count',
 'other_thread_get','finish_pending','duplicate_get','finish_mismatch','overflow','begin_twice','retained_batches',
 'range_equal','range_bounds','range_mismatch','range_wrong_owner','range_pending')


def record(path):
    path=path.resolve()
    with path.open('rb')as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(path=str(path),bytes=path.stat().st_size,sha256=digest)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(exist_ok=False)
    base=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    native=a.workspace/'toolchain/llvm-mingw-20261006-ucrt-x86_64/bin/clang++.exe'
    sdk=a.workspace/'toolchain/ps5-sdk-radv/ps5-payload-sdk'
    libs=[]
    for name in ('ggml.a','ggml-cpu.a','ggml-base.a'):
        candidates=list((a.cache/'host-CPU-reference-066/build').rglob(name))+list((a.cache/'host-CPU-reference-066/build').rglob('lib'+name))
        if len(candidates)!=1:raise ValueError('The exact existing host CPU libraries are required')
        libs.append(candidates[0])
    source=ROOT/'native/app/completed_expert_routes.cpp';test=ROOT/'tests/completed_expert_routes.cpp'
    inputs=[record(p)for p in (source,source.with_suffix('.h'),test,Path(__file__),*libs,
        base/'ggml/include/ggml.h',base/'ggml/include/ggml-backend.h',host/'clang++.exe',native)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    executable=a.out/'completed-expert-routes.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
        '-I',str(base/'ggml/include'),str(source),str(test),'-Wl,--start-group',*map(str,libs),'-Wl,--end-group','-o',str(executable)]
    steps=[]
    def run(name,cmd):
        result=subprocess.run(cmd,env=env,capture_output=True,timeout=120)
        (a.out/(name+'.private.log')).write_bytes(result.stdout+result.stderr)
        steps.append(dict(name=name,returncode=result.returncode))
        if result.returncode:raise RuntimeError('Completed expert route '+name+' failed; see retained log')
        return result
    run('compile',command)
    cases=[]
    for scenario in SCENARIOS:cases.append(json.loads(run(scenario,[str(executable),scenario]).stdout))
    object_path=a.out/'completed-expert-routes-PS5.o'
    command=[str(native),'--no-default-config','--target=x86_64-sie-ps5','-fno-stack-protector','-fno-plt',
        '-femulated-tls','-fdenormal-fp-math=ieee','-fPIC','-std=c++17','-O1','-DNDEBUG',
        '-fvisibility-nodllstorageclass=default','-fexceptions','-fcxx-exceptions','-frtti','-nostdinc++',
        '-isystem',str(sdk/'target/include/c++/v1'),'-isystem',str(sdk/'target/include'),
        '-I',str(ROOT/'native/app'),'-I',str(base/'ggml/include'),'-c',str(source),'-o',str(object_path)]
    run('PS5_object',command)
    if inputs!=[record(Path(row['path']))for row in inputs]:raise ValueError('A checked observer input changed')
    result=dict(schema='ps5-qwen-completed-expert-routes-host-v1',inputs=inputs,steps=steps,
        actual_GGML_CPU_provider=True,scenarios=cases,PS5_object=record(object_path),
        console_requests=0,GPU_calls=0,learned_model_inference=False,native_link_and_physical_qualification_pending=True)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(host_cases=len(cases),all_passed=True,actual_GGML_CPU_provider=True,PS5_object_compiled=True,console_requests=0)))
if __name__=='__main__':main()
