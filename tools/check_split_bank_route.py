#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check real partial-shape metadata and compile the actual native fixture."""
import argparse,json,os,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in('workspace','cache','qualified-native','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    libraries=list((a.cache/'host-CPU-reference-066/build').rglob('*ggml-base.a'))
    if len(libraries)!=1:raise ValueError('One exact existing metadata provider required')
    test=ROOT/'tests/split_bank_route.cpp';source=ROOT/'native/app/padded_bank_route.cpp';exe=a.out/'split-route.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
        '-I',str(up/'ggml/include'),str(test),str(source),str(libraries[0]),'-o',str(exe)],[str(exe)]]
    prior=json.loads(a.qualified_native.read_text())
    original=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    native_sources=[ROOT/'native/app'/name for name in('ready_expert_fixture.cpp','split_bank_admission.cpp','padded_bank_route.cpp')]
    for src in native_sources:
        cmd=original.copy();cmd[cmd.index('-c')+1]=str(src);cmd[cmd.index('-o')+1]=str(a.out/(src.stem+'-PS5.o'))
        cmd+=['-Wall','-Wextra','-Werror'];commands.append(cmd)
    files=[Path(__file__),test,source,libraries[0],a.qualified_native,*native_sources,*sorted((ROOT/'native/app').glob('*.h'))]
    inputs=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls=None
    for i,cmd in enumerate(commands):
        r=subprocess.run(cmd,capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Split route '+str(i)+': '+(r.stdout+r.stderr).decode(errors='replace')[-5000:])
        if i==1:controls=json.loads(r.stdout)
    assert controls['actual_GGML_partial_shapes']==80 and controls['altered_layout_refusals']==1600
    assert inputs==[record(f)for f in files]
    receipt=dict(schema='ps5-qwen-split-route-host-v1',inputs=inputs,commands=commands,controls=controls,
        native_SDK_objects=[record(a.out/(s.stem+'-PS5.o'))for s in native_sources],PS5_operations=0,CI_runs=0,
        native_GPU_arithmetic_qualified=False)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(controls),flush=True)
if __name__=='__main__':main()
