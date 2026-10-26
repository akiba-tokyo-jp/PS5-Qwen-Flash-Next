#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Manual geometry, exact-byte and returned-failure controls; no console access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    runtime=args.workspace/'toolchain/msys-clang64/clang64/bin'
    executable=args.out/'vector-delivery-tests.exe'
    command=[str(runtime/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
             '-Dpread=qwen_vector_test_pread','-include',str(ROOT/'tests/vector_delivery_host.h'),
             '-I',str(ROOT/'native/app'),'-I',str(ROOT/'native/qwen_flash_next'),
             str(ROOT/'native/qwen_flash_next/vector_delivery_probe_cpp.cpp'),str(ROOT/'tests/vector_delivery.cpp'),
             '-o',str(executable)]
    env=dict(os.environ,PATH=str(runtime)+os.pathsep+os.environ.get('PATH',''))
    for label,cmd in [('compile',command),('run',[str(executable)])]:
        result=subprocess.run(cmd,env=env,capture_output=True,timeout=90)
        (args.out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(label+' failed: '+result.stderr.decode(errors='replace')[-2400:])
    receipt=dict(controls=json.loads(result.stdout),command=command,source_sha256={
        str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()for path in [
            ROOT/'native/qwen_flash_next/vector_delivery_probe_cpp.cpp',ROOT/'native/app/demand_source_batch.h',
            ROOT/'native/app/completion_source_io.h',ROOT/'tests/vector_delivery.cpp',
            ROOT/'tests/vector_delivery_host.h']},CI=False)
    (args.out/'receipt.private.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt['controls']),flush=True)


if __name__=='__main__':main()
