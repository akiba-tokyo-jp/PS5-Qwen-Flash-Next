#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually verify demand-worker ownership and refill; no console, model or CI."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(p):
    p=Path(p).resolve();return dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    runtime=args.workspace/'toolchain/msys-clang64/clang64';exe=args.out/'demand-source-batch.exe'
    env=dict(os.environ,PATH=str(runtime/'bin')+os.pathsep+os.environ.get('PATH',''))
    commands=[[runtime/'bin/clang++.exe','-std=c++17','-O3','-Wall','-Wextra','-Werror',
        '-I',ROOT/'native/app',ROOT/'tests/demand_source_batch.cpp','-o',exe],[exe]]
    for i,command in enumerate(commands):
        result=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=60)
        (args.out/f'step-{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-2400:])
    proof=dict(controls=json.loads(result.stdout),inputs=[record(p)for p in (Path(__file__),ROOT/'native/app/demand_source_batch.h',
        ROOT/'native/app/completion_source_io.h',ROOT/'tests/demand_source_batch.cpp')],
        executable=record(exe),commands=[list(map(str,c))for c in commands],PS5_operations=0,CI_runs=0)
    (args.out/'receipt.private.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof['controls']),flush=True)
if __name__=='__main__':main()
