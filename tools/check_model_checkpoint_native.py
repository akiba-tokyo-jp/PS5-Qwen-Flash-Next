#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check exact checkpoint policy and compile the actual native integration."""
import argparse,json,os,subprocess
from pathlib import Path
from check_model_checkpoint import record
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('workspace','cache','policy','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);(a.out/'tmp').mkdir();up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569'
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'model-policy-tests.exe'
    commands=[[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'vendor'),str(ROOT/'tests/model_checkpoint_policy.cpp'),'-o',str(exe)],[str(exe),str(a.policy)]]
    prior=json.loads((a.cache/'build/application-native-palette-2556/receipt.private.json').read_text())
    for name in ('llama_engine.cpp','model_checkpoint.cpp','native_main.cpp'):
        source_name='llama_engine.cpp'if name=='model_checkpoint.cpp'else name
        c=next(c for c in prior['compile_commands']if Path(c[c.index('-c')+1]).name==source_name).copy()
        c[c.index('-c')+1]=str(ROOT/'native/app'/name);c[c.index('-o')+1]=str(a.out/(name+'.o'));c+=['-Wall','-Wextra','-Werror'];commands.append(c)
        if name=='native_main.cpp':
            for i in range(len(c)-1):
                if c[i]=='-I'and Path(c[i+1])==up/'common':c[i]='-isystem'
    files=[ROOT/'native/app'/n for n in ('llama_engine.cpp','llama_engine.h','model_checkpoint.cpp','model_checkpoint.h','model_checkpoint_policy.h','native_main.cpp','completed_expert_routes.h','completed_expert_routes.cpp','validation_policy.h')]
    files+=[ROOT/'tests/model_checkpoint_policy.cpp',a.policy,Path(__file__)];fixed=[record(p)for p in files]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''),TMP=str(a.out/'tmp'),TEMP=str(a.out/'tmp'));controls=None
    for i,c in enumerate(commands):
        r=subprocess.run(c,capture_output=True,timeout=300,env=env);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Native check '+str(i)+': '+r.stderr.decode(errors='replace')[-4000:])
        if i==1:controls=json.loads(r.stdout)
    assert fixed==[record(p)for p in files]
    result=dict(host_policy=controls,all_three_native_units_compiled=True,inputs=fixed,commands=commands,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ('inputs','commands')}),flush=True)
if __name__=='__main__':main()
