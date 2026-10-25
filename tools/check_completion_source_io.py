#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manually build and check bounded completion-driven source ownership."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    host=a.workspace/'toolchain/msys-clang64/clang64';exe=a.out/'completion-source-check.exe'
    commands=[[str(host/'bin/clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(R/'native/app'),
        str(R/'tests/completion_source_io.cpp'),'-o',str(exe)],[str(exe)]]
    env=dict(os.environ,PATH=str(host/'bin')+os.pathsep+os.environ.get('PATH',''))
    for i,command in enumerate(commands):
        result=subprocess.run(command,capture_output=True,timeout=60,env=env)
        (a.out/f'step-{i}.private.log').write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-2500:])
    controls=json.loads(result.stdout)
    inputs=[dict(path=str(x),bytes=x.stat().st_size,sha256=hashlib.sha256(x.read_bytes()).hexdigest())for x in
        [Path(__file__),R/'tests/completion_source_io.cpp',R/'native/app/completion_source_io.h']]
    (a.out/'receipt.private.json').write_text(json.dumps(dict(inputs=inputs,commands=commands,controls=controls,
        PS5_operations=0,CI_runs=0),indent=2)+'\n');print(json.dumps(controls),flush=True)
if __name__=='__main__':main()
