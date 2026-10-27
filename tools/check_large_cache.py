#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually check 53/128-slot dispatch and owned reads without a console."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workspace','cache','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    source=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    app=ROOT/'native/app';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    planner=source/'ggml/src/ggml-backend.cpp';raw=planner.read_bytes()
    if hashlib.sha256(raw).hexdigest()!='79ade6b83b3d042e43e035fa81d2c672211a552af9af38e410a047e4ba2723a0':
        raise ValueError('Pinned original buffer planner required')
    text=raw.decode();first=text.index('struct ggml_backend_buft_alloc_buffer_n_plan_item {')
    last=text.index('// default implementation of alloc_buffer_n',first)
    inc=a.out/'actual_padded_buffer_plan.inc';inc.write_text(text[first:last],newline='\n')
    steps=[];inputs=[Path(__file__),planner,inc]
    for name in ('padded_bank','padded_source','padded_buffer_plan','large_cache_policy'):
        units=[ROOT/'tests'/(name+'.cpp')]
        if name=='padded_bank':units.append(app/'padded_bank_route.cpp')
        exe=a.out/(name+'.exe')
        commands=[['compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror',
            '-I',app,'-I',source/'ggml/include','-I',source/'vendor','-I',a.out,*units,'-o',exe]]]
        commands.append(['default',[exe]])
        if name!='large_cache_policy':commands.append(['128_slots',[exe,'--large']])
        for label,command in commands:
            r=subprocess.run(list(map(str,command)),capture_output=True,timeout=180,env=env)
            (a.out/(name+'-'+label+'.private.log')).write_bytes(r.stdout+r.stderr)
            steps.append(dict(name=name+'_'+label,returncode=r.returncode))
            if r.returncode:raise RuntimeError(r.stderr.decode('utf-8','replace')[-4000:])
            print(name+' '+label+' passed',flush=True)
        inputs+=units
    inputs+=list(app.glob('*.h'))
    (a.out/'receipt.private.json').write_text(json.dumps(dict(schema='ps5-qwen-large-cache-host-check-v1',
        steps=steps,inputs={str(path):hashlib.sha256(path.read_bytes()).hexdigest()for path in inputs},
        PS5_operations=0,GPU_calls=0,CI_runs=0,native_allocation_qualified=False),indent=2)+'\n')
if __name__=='__main__':main()
