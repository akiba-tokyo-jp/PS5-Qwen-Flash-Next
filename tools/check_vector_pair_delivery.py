#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify actual two-expert executor scatter mapping and known failure retirement."""
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
    runtime=a.workspace/'toolchain/msys-clang64/clang64/bin';exe=a.out/'vector-pair-tests.exe'
    cmd=[str(runtime/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-DQWEN_VECTOR_HOST_STUB',
         '-Dpread=qwen_vector_test_pread','-Dpreadv=qwen_vector_test_preadv',
         '-include',str(ROOT/'tests/vector_delivery_host.h'),'-I',str(ROOT/'tests/vector_pair_stubs'),
         '-I',str(ROOT/'native/app'),'-I',str(ROOT/'native/qwen_flash_next'),
         str(ROOT/'native/qwen_flash_next/vector_pair_probe_cpp.cpp'),str(ROOT/'tests/vector_pair_delivery.cpp'),'-o',str(exe)]
    env=dict(os.environ,PATH=str(runtime)+os.pathsep+os.environ.get('PATH',''))
    for label,command in [('compile',cmd),('run',[str(exe)])]:
        r=subprocess.run(command,env=env,capture_output=True,timeout=60)
        (a.out/(label+'.private.log')).write_bytes(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(label+' failed: '+r.stderr.decode(errors='replace')[-2400:])
    receipt=dict(controls=json.loads(r.stdout),command=cmd,source_sha256={
        str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in [
            ROOT/'native/app/vectored_source_batch.h',ROOT/'native/qwen_flash_next/vector_pair_probe_cpp.cpp',
            ROOT/'tests/vector_pair_delivery.cpp',ROOT/'tests/vector_delivery_host.h',
            ROOT/'tests/vector_pair_stubs/sys/uio.h']},CI=False)
    (a.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt['controls']),flush=True)


if __name__=='__main__':main()
