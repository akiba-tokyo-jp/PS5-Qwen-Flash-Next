#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run focused memory-counter and evidence controls without contacting a console."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    exe=a.out/'memory-counters.exe'
    commands=[('counter-compile',[host/'clang.exe','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-I',ROOT/'native/app',ROOT/'tests/kernel_memory_trace.c','-o',exe]),
        ('counter-controls',[exe]),
        ('evidence-controls',[sys.executable,'-B',ROOT/'tests/test_kernel_memory_trace_result.py'])]
    steps=[]
    for label,command in commands:
        result=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=120)
        (a.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-2500:])
        steps.append(dict(name=label,returncode=0));print(label+' passed',flush=True)
    sources=[Path(__file__),ROOT/'native/app/kernel_memory_trace.h',ROOT/'tests/kernel_memory_trace.c',
        ROOT/'tools/kernel_memory_trace_result.py',ROOT/'tests/test_kernel_memory_trace_result.py']
    receipt=dict(steps=steps,inputs=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in sources],
        PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
