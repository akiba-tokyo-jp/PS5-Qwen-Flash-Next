#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare the native streaming hash with Python SHA256 and reject mutation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);a=p.parse_args()
    lock=json.loads((ROOT/'native/qwen_flash_next/dependencies.lock.json').read_text())
    upstream=a.cache/'upstream'/('llama.cpp-'+lock['llama_cpp']['revision'])
    out=a.cache/'build/model-integrity-check';out.mkdir(parents=True,exist_ok=True)
    host=a.workspace/'toolchain/msys-clang64/clang64/bin';env=dict(os.environ,PATH=str(host)+os.pathsep+os.environ.get('PATH',''))
    exe=out/'integrity-tests.exe'
    command=[str(host/'clang++.exe'),'-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I',str(ROOT/'native/app'),'-I',str(upstream/'vendor'),'-I',str(upstream/'vendor/hash'),
        *[str(ROOT/name)for name in ('native/app/model_integrity.cpp','native/app/sha256_backend.cpp','tests/model_integrity.cpp')],'-o',str(exe)]
    result=subprocess.run(command,env=env,capture_output=True,timeout=90)
    (out/'compile.private.log').write_bytes(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace'))
    data=bytes(range(256))*(int((65<<20)/256))+b'boundary';fixture=out/'fixture.private.dat';fixture.write_bytes(data)
    digest=hashlib.sha256(data).hexdigest()
    for label,args,success in [('correct',[str(exe),str(fixture),digest],True),
        ('wrong_digest',[str(exe),str(fixture),'0'*64],False),
        ('mutated',[str(exe),str(fixture),digest,'mutate'],False)]:
        result=subprocess.run(args,env=env,capture_output=True,timeout=90)
        (out/(label+'.private.log')).write_bytes(result.stdout+result.stderr)
        if (result.returncode==0)!=success:raise RuntimeError('Native integrity outcome is incorrect: '+label)
        print(label+' passed',flush=True)
    (out/'receipt.private.json').write_text(json.dumps(dict(independent_SHA256_match=True,
        digest_mismatch_rejected=True,file_growth_rejected=True,buffer_bytes=1<<20,
        console_access=False,model_loaded=False,GPU_execution=False),indent=2)+'\n')
if __name__=='__main__':main()
