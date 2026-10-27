#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check actual ten-Expert source ownership with metadata and compile PS5 objects."""
import argparse,json,os,subprocess
from pathlib import Path
from build_preservation_integrity import record
ROOT=Path(__file__).resolve().parents[1]
SCENARIOS=('parser','one-graph','split-serial','split-overlap','identity','short','byte-proof','read-exception','memory','close','GPU-refusal','CPU-one','CPU-two','CPU-scope','CPU-short','CPU-close')
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in('workspace','cache','plan','qualified-native','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--compiled-plan',type=Path,help='Check the exact private manifest embedded by the native build')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    src=ROOT/'native/app/ready_original_source.cpp';test=ROOT/'tests/ready_original_source.cpp';sha=up/'vendor/hash/sha256/sha256.c';obj=a.out/'sha.o';exe=a.out/'original-source.exe'
    common=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'ggml/include'),'-isystem',str(up/'vendor')]
    if a.compiled_plan:common+=['-DQWEN_READY_ORIGINAL_PLAN=1','-I',str(a.compiled_plan.parent)]
    commands=[[str(host/'clang.exe'),'-O2','-I',str(up/'vendor/hash'),'-c',str(sha),'-o',str(obj)],common+[str(test),str(src),str(obj),'-o',str(exe)]]
    commands += [[str(exe),str(a.plan),s]for s in SCENARIOS]
    namespace_test=ROOT/'tests/ready_original_namespace.cpp';namespace_exe=a.out/'original-namespace.exe'
    commands += [common+[str(namespace_test),'-o',str(namespace_exe)],[str(namespace_exe)]]
    prior=json.loads(a.qualified_native.read_text());original=next(c.copy()for c in prior['compile_commands']if '-c'in c and Path(c[c.index('-c')+1]).name=='native_main.cpp')
    for name in('ready_original_source.cpp','ready_expert_fixture.cpp','split_bank_admission.cpp'):
        c=original.copy();c[c.index('-c')+1]=str(ROOT/'native/app'/name);c[c.index('-o')+1]=str(a.out/(Path(name).stem+'-PS5.o'));c+=['-Wall','-Wextra','-Werror'];commands.append(c)
        if a.compiled_plan and name=='ready_original_source.cpp':c+=['-DQWEN_READY_ORIGINAL_PLAN=1','-I',str(a.compiled_plan.parent)]
    files=[Path(__file__),src,test,namespace_test,sha,a.plan,a.qualified_native,*sorted((ROOT/'native/app').glob('*.h')),ROOT/'native/app/ready_expert_fixture.cpp',ROOT/'native/app/split_bank_admission.cpp']
    if a.compiled_plan:files.append(a.compiled_plan)
    inputs=[record(f)for f in files];env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''));controls=[]
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/f'{i}.private.log').write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Original source '+str(i)+': '+(r.stdout+r.stderr).decode(errors='replace')[-5000:])
        if 2<=i<2+len(SCENARIOS):controls.append(dict(scenario=SCENARIOS[i-2],**json.loads(r.stdout)))
    assert all(r['passed']and r['PS5_operations']==r['file_reads']==r['GPU_calls']==0 for r in controls)
    assert inputs==[record(f)for f in files]
    receipt=dict(schema='ps5-qwen-ready-original-source-host-v1',inputs=inputs,commands=commands,controls=controls,
        native_SDK_compiled=True,native_arithmetic_or_speed_qualified=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(scenarios=len(controls),native_SDK_compiled=True,PS5_operations=0)),flush=True)
if __name__=='__main__':main()
