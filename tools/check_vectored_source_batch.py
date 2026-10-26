#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manual vector-request ownership, bounds and known/unknown completion controls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    runtime=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'vectored-source-tests.exe'
    command=[str(runtime/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),
             str(ROOT/'tests/vectored_source_batch.cpp'),'-o',str(exe)]
    env=dict(os.environ,PATH=str(runtime)+os.pathsep+os.environ.get('PATH',''));controls={}
    for label,cmd in [('compile',command),('normal',[str(exe)]),('unknown',[str(exe),'--unknown'])]:
        r=subprocess.run(cmd,env=env,capture_output=True,timeout=30)
        (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(label+' failed: '+r.stderr.decode(errors='replace')[-2000:])
        if label!='compile':controls[label]=json.loads(r.stdout)
    receipt=dict(controls=controls,command=command,inputs={
        str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [
            ROOT/'native/app/vectored_source_batch.h',ROOT/'tests/vectored_source_batch.cpp']},
        PS5_operations=0,learned_inference=False,CI=False)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(controls),flush=True)


if __name__=='__main__':main()
