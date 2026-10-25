#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Focused manual CPU queue controls, including retained uncertain backing."""
import argparse,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    exe=a.out/'queued_source.exe';steps=[]
    for name,command in [('compile',[host/'clang++.exe','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',ROOT/'native/app',ROOT/'tests/queued_source.cpp','-o',exe]),
                         ('completed_controls',[exe]),('uncertain_backing_retained',[exe,'uncertain'])]:
        r=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=60)
        (a.out/(name+'.private.log')).write_bytes(r.stdout+r.stderr);steps.append(dict(name=name,returncode=r.returncode))
        if r.returncode:raise RuntimeError(r.stderr.decode('utf-8','replace')[-2500:])
        print(name+' passed',flush=True)
    (a.out/'receipt.private.json').write_text(json.dumps(dict(steps=steps,CPU_only=True,console_requests=0,GPU_calls=0),indent=2)+'\n')
if __name__=='__main__':main()
