#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check bounded batch recording and uncertainty retention without console access."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(p):
    return dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'batch-journal-tests.exe'
    files=[ROOT/'native/app/batch_io_journal.h',ROOT/'tests/batch_io_journal.cpp',Path(__file__)];fixed=[record(p)for p in files]
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),str(files[1]),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,cmd in enumerate([command,[str(exe)]]):
        r=subprocess.run(cmd,capture_output=True,timeout=90,env=env);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2500:])
    assert fixed==[record(p)for p in files]
    result=json.loads(r.stdout);result.update(inputs=fixed,command=command,console_calls=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in ('inputs','command')}),flush=True)
if __name__=='__main__':main()
