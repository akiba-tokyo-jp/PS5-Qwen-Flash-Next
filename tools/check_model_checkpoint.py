#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check bounded checkpoint transactions with API stubs, never model inference."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(p):return dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('workspace','cache','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);up=a.cache/'upstream/llama.cpp-0a1ef309cdbb9f2024f58a38fb4c42352c5db569';host=a.workspace/'toolchain/msys-clang64/clang64/bin'
    files=[ROOT/'native/app/model_checkpoint.h',ROOT/'native/app/model_checkpoint.cpp',ROOT/'tests/model_checkpoint.cpp',up/'include/llama.h',Path(__file__)];fixed=[record(p)for p in files]
    exe=a.out/'checkpoint-tests.exe';command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/app'),'-I',str(up/'include'),'-I',str(up/'ggml/include'),str(files[1]),str(files[2]),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate([command,[str(exe)]]):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3000:])
    assert fixed==[record(p)for p in files]
    result=dict(controls=json.loads(r.stdout),inputs=fixed,command=command,API_stubs_only=True,full_model_checkpoint_native_qualified=False,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['controls']),flush=True)
if __name__=='__main__':main()
