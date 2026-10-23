#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Test the actual native observation function and strict physical budget gate."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir()
    source=ROOT/'native/app/native_gpu.cpp';text=source.read_text()
    start=text.index('qwen_app::NativeAllocatorBudget qwen_native_allocator_budget(');begin=text.index('{',start);level=1;end=begin+1
    while level:
        level+=(text[end]=='{')-(text[end]=='}');end+=1
    (a.out/'actual_native_allocator_budget.h').write_text(text[start:end]+'\n',encoding='utf-8',newline='\n')
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'native-allocator-budget.exe'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(a.out),str(ROOT/'tests/native_allocator_budget.cpp'),'-o',str(exe)]
    for label,cmd in [('compile',command),('run',[str(exe)])]:
        r=subprocess.run(cmd,env=env,capture_output=True,timeout=120);(a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('Actual native allocator '+label+' failed')
    (a.out/'receipt.private.json').write_text(json.dumps(dict(actual_native_observation='passed',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),budget_header_sha256=hashlib.sha256((ROOT/'native/app/native_allocator_budget.h').read_bytes()).hexdigest(),console_access=False,GPU_calls=0,allocation_calls=0),indent=2)+'\n')
    print(r.stdout.decode(),end='')
if __name__=='__main__':main()
