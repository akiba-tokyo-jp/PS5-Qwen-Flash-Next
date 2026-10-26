#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check real-descriptor geometry with the actual bounded layout executor."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def record(p):return dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);host=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'layout-tests.exe'
    files=[ROOT/'native/qwen_flash_next'/n for n in ('vector_layout_delivery.h','vector_layout_delivery.cpp')]+[ROOT/'native/app'/n for n in ('vectored_source_batch.h','batch_io_journal.h')]+[ROOT/'tests/vector_layout_delivery.cpp',Path(__file__)]
    fixed=[record(p)for p in files]
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-DQWEN_VECTOR_HOST_STUB','-Dpread=qwen_vector_test_pread','-Dpreadv=qwen_vector_test_preadv',
        '-include',str(ROOT/'tests/vector_delivery_host.h'),'-I',str(ROOT/'tests/vector_pair_stubs'),'-I',str(ROOT/'native/app'),'-I',str(ROOT/'native/qwen_flash_next'),str(files[1]),str(ROOT/'tests/vector_layout_delivery.cpp'),'-o',str(exe)]
    env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    for i,c in enumerate([command,[str(exe)]]):
        r=subprocess.run(c,capture_output=True,timeout=120,env=env);(a.out/(str(i)+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-3000:])
    assert fixed==[record(p)for p in files]
    result=dict(controls=json.loads(r.stdout),inputs=fixed,command=command,PS5_operations=0,CI_runs=0)
    (a.out/'receipt.private.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['controls']),flush=True)
if __name__=='__main__':main()
